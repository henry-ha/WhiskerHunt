#if ANDROID
using Android.Content;
using Android.Graphics;
using Android.Opengl;
using Java.Nio;
using System.Buffers.Binary;
using System.Globalization;
using System.Numerics;
using System.Text;
using System.Text.Json;
using GLES = Android.Opengl.GLES20;
using GlMatrix = Android.Opengl.Matrix;

namespace WhiskerHunt;

/// <summary>
/// Native OpenGL ES 2.0 textured glTF 2.0/GLB animal model renderer.
/// Models are embedded as MAUI assets, decoded on-device and rendered at the
/// ARCore world anchor (not a camera-locked sprite or primitive placeholder).
/// Currently supports static triangular meshes, PBR base-colour textures,
/// node transforms, float position/normal/UV, and 8/16/32-bit mesh indices.
/// For rigged assets: export a frozen rest-pose STATIC mesh/GLB first.
/// </summary>
internal sealed class HushGlbAnimal3D
{
    private sealed class Part
    {
        public FloatBuffer Positions = null!;
        public FloatBuffer Normals = null!;
        public FloatBuffer Uvs = null!;
        public int Count;
        public int MaterialIndex;
    }
    private sealed class SurfaceMaterial
    {
        public byte[]? Image;
        public int GlTexture;
        public float[] Factor = { 1, 1, 1, 1 };
    }
    private readonly List<Part> _parts = new();
    private readonly List<SurfaceMaterial> _materials = new();
    private readonly string _label;
    private readonly float _displaySizeMetres;
    private readonly float[] _min = { float.MaxValue, float.MaxValue, float.MaxValue };
    private readonly float[] _max = { float.MinValue, float.MinValue, float.MinValue };
    private readonly float[] _model = new float[16], _vm = new float[16], _mvp = new float[16];
    private int _program, _position, _normal, _uv, _mvpLoc, _modelLoc, _colorLoc, _textureLoc;
    private int _whiteTexture;

    private HushGlbAnimal3D(string label, float displaySizeMetres)
    { _label = label; _displaySizeMetres = displaySizeMetres; }

    // Prevents generic family-level stand-ins being displayed as specific species.
    // To add more: package ar_models/<family>-<variety>.glb with rights to redistribute.
    public static bool TryLoad(Context context, string group, string variety, out HushGlbAnimal3D? result, out string message)
    {
        result = null;
        var filename = Slug(group) + "-" + Slug(variety) + ".glb";
        if (string.IsNullOrWhiteSpace(variety) || filename.Length > 125)
        { message = "This animal does not have a matching 3D model yet."; return false; }
        try
        {
            using var file = context.Assets!.Open("ar_models/" + filename);
            using var ms = new MemoryStream();
            file.CopyTo(ms);
            if (ms.Length > 24 * 1024 * 1024) throw new InvalidDataException("The 3D model exceeds 24 MB.");
            // Large enough to inspect but deliberately scaled for accessibility;
            // adult animals should use individually calibrated physical dimensions.
            float scale = group.ToLowerInvariant() switch
            {
                "snail" => .22f, "ladybird" or "spider" or "bee" or "butterfly" or "ant" or "beetle" => .13f,
                "cat" => .47f, "dog" => .65f, "rabbit" => .35f, "bird" => .32f,
                "squirrel" => .31f, "hedgehog" => .24f, "frog" => .20f,
                "other" when variety.Equals("Deer", StringComparison.OrdinalIgnoreCase) => 1.05f,
                "other" when variety.Equals("Fox", StringComparison.OrdinalIgnoreCase) => .65f,
                "other" when variety.Equals("Tortoise", StringComparison.OrdinalIgnoreCase) => .35f,
                _ => .30f
            };
            var model = new HushGlbAnimal3D(variety, scale);
            model.Parse(ms.ToArray());
            if (model._parts.Count == 0) throw new InvalidDataException("No supported triangular geometry in this model.");
            result = model;
            message = "Textured 3D " + variety + " model ready.";
            return true;
        }
        catch (Java.IO.FileNotFoundException)
        {
            message = "There is no detailed 3D asset for " + variety + " yet. Opening 2D Safari avoids an inaccurate animal.";
            return false;
        }
        catch (FileNotFoundException)
        {
            message = "There is no detailed 3D asset for " + variety + " yet. Use 2D Safari.";
            return false;
        }
        catch (Exception e)
        {
            message = "The " + variety + " 3D model is unavailable (" + e.GetType().Name + "). Use 2D Safari.";
            return false;
        }
    }

    private static string Slug(string value)
    {
        var sb = new StringBuilder();
        foreach (var c in value.ToLowerInvariant())
        {
            if (c >= 'a' && c <= 'z' || c >= '0' && c <= '9') sb.Append(c);
            else if (sb.Length > 0 && sb[^1] != '-') sb.Append('-');
        }
        return sb.ToString().Trim('-');
    }
    private static FloatBuffer Direct(float[] values)
    {
        FloatBuffer b = ByteBuffer.AllocateDirect(values.Length * 4)
            .Order(ByteOrder.NativeOrder()).AsFloatBuffer();
        b.Put(values); b.Position(0); return b;
    }
    private static bool Has(JsonElement el, string key) => el.ValueKind == JsonValueKind.Object && el.TryGetProperty(key, out _);
    private static int Int(JsonElement el, string key, int fallback = 0) =>
        Has(el, key) ? el.GetProperty(key).GetInt32() : fallback;
    private static float[] Numbers(JsonElement el, string key, float[] fallback)
    {
        if (!Has(el, key)) return fallback;
        return el.GetProperty(key).EnumerateArray().Select(x => x.GetSingle()).ToArray();
    }
    private static int BytesPer(int component) => component switch
    { 5120 or 5121 => 1, 5122 or 5123 => 2, 5125 or 5126 => 4, _ => throw new InvalidDataException("Unsupported accessor type: " + component) };

    private void Parse(byte[] file)
    {
        if (file.Length < 32 || BinaryPrimitives.ReadUInt32LittleEndian(file.AsSpan(0, 4)) != 0x46546C67 ||
            BinaryPrimitives.ReadUInt32LittleEndian(file.AsSpan(4, 4)) != 2 ||
            BinaryPrimitives.ReadUInt32LittleEndian(file.AsSpan(8, 4)) != (uint)file.Length)
            throw new InvalidDataException("Expected glTF 2.0 binary GLB.");
        int p = 12; byte[]? binary = null; byte[]? jsonBytes = null;
        while (p + 8 <= file.Length)
        {
            int size = checked((int)BinaryPrimitives.ReadUInt32LittleEndian(file.AsSpan(p, 4)));
            int type = (int)BinaryPrimitives.ReadUInt32LittleEndian(file.AsSpan(p + 4, 4));
            p += 8;
            if (size < 0 || size > file.Length - p) throw new InvalidDataException("Invalid GLB chunk.");
            if (type == 0x4E4F534A) jsonBytes = file.AsSpan(p, size).ToArray();
            if (type == 0x004E4942) binary = file.AsSpan(p, size).ToArray();
            p += size;
        }
        if (jsonBytes is null || binary is null) throw new InvalidDataException("Missing GLB JSON/BIN chunk.");
        using var parsed = JsonDocument.Parse(jsonBytes);
        var root = parsed.RootElement;
        var views = root.GetProperty("bufferViews");
        var accessors = root.GetProperty("accessors");
        var meshes = root.GetProperty("meshes");
        var nodes = root.GetProperty("nodes");

        byte[] ReadView(int index)
        {
            var view = views[index];
            if (Int(view, "buffer") != 0) throw new InvalidDataException("Only internal GLB buffers supported.");
            int offset = Int(view, "byteOffset"), length = Int(view, "byteLength");
            if (offset < 0 || length < 0 || offset > binary.Length - length) throw new InvalidDataException("Invalid buffer view.");
            return binary.AsSpan(offset, length).ToArray();
        }
        float[] ReadFloats(int accessorIndex, int components)
        {
            var accessor = accessors[accessorIndex];
            int count = Int(accessor, "count"), componentType = Int(accessor, "componentType");
            if (componentType != 5126 || count > 350000 || count < 0 ||
                accessor.GetProperty("type").GetString() != "VEC" + components)
                throw new InvalidDataException("Expected float VEC" + components + " attribute.");
            int viewIndex = Int(accessor, "bufferView"), offset = Int(accessor, "byteOffset");
            var view = views[viewIndex];
            byte[] data = ReadView(viewIndex);
            int stride = Int(view, "byteStride", components * 4);
            if (stride < components * 4 || offset < 0 || (long)offset + (long)Math.Max(0,count-1)*stride + components*4 > data.Length)
                throw new InvalidDataException("Invalid float accessor stride.");
            float[] values = new float[count * components];
            for (int i=0;i<count;i++) for (int c=0;c<components;c++)
                values[i*components+c] = BitConverter.Int32BitsToSingle(BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(offset+i*stride+c*4,4)));
            return values;
        }
        int[] ReadIndices(int accessorIndex)
        {
            var accessor = accessors[accessorIndex];
            int count = Int(accessor,"count"), cType = Int(accessor,"componentType");
            if (count < 0 || count > 4000000 || accessor.GetProperty("type").GetString() != "SCALAR") throw new InvalidDataException("Invalid indices.");
            int vi = Int(accessor,"bufferView"), offset = Int(accessor,"byteOffset"), size=BytesPer(cType);
            byte[] data = ReadView(vi);
            int stride=Int(views[vi],"byteStride",size);
            if (stride<size || offset < 0 || (long)offset+(long)Math.Max(0,count-1)*stride+size>data.Length)throw new InvalidDataException("Invalid index buffer.");
            int[] values = new int[count];
            for (int i=0;i<count;i++)
            {
                var cell=data.AsSpan(offset+i*stride,size);
                values[i]=cType switch {
                    5121 => cell[0], 5123 => BinaryPrimitives.ReadUInt16LittleEndian(cell),
                    5125 => checked((int)BinaryPrimitives.ReadUInt32LittleEndian(cell)),
                    _ => throw new InvalidDataException("Unsupported index type")};
            }
            return values;
        }
        // Android GLUtils converts PNG/JPEG pixels to an actual GPU texture later.
        if (Has(root,"materials"))
        {
            foreach(var material in root.GetProperty("materials").EnumerateArray())
            {
                var current=new SurfaceMaterial();
                if (Has(material,"pbrMetallicRoughness"))
                {
                    var pbr=material.GetProperty("pbrMetallicRoughness");
                    current.Factor=Numbers(pbr,"baseColorFactor",new float[]{1,1,1,1});
                    if (Has(pbr,"baseColorTexture") && Has(root,"textures") && Has(root,"images"))
                    {
                        int textureIndex=Int(pbr.GetProperty("baseColorTexture"),"index");
                        int source=Int(root.GetProperty("textures")[textureIndex],"source");
                        var image=root.GetProperty("images")[source];
                        if (Has(image,"bufferView"))current.Image=ReadView(Int(image,"bufferView"));
                    }
                }
                _materials.Add(current);
            }
        }
        if (_materials.Count==0)_materials.Add(new SurfaceMaterial());

        void ParsePrimitive(JsonElement primitive,float[] transform)
        {
            if (Int(primitive,"mode",4)!=4) return; // triangles only, no fans or strips
            var attrs=primitive.GetProperty("attributes");
            if (!Has(attrs,"POSITION"))return;
            float[] pos=ReadFloats(Int(attrs,"POSITION"),3);
            float[]? uv=Has(attrs,"TEXCOORD_0")?ReadFloats(Int(attrs,"TEXCOORD_0"),2):null;
            float[]? normal=Has(attrs,"NORMAL")?ReadFloats(Int(attrs,"NORMAL"),3):null;
            int vertexCount=pos.Length/3;
            int[] indices=Has(primitive,"indices")?ReadIndices(Int(primitive,"indices")):Enumerable.Range(0,vertexCount).ToArray();
            if (indices.Length>900000 || indices.Length%3!=0)throw new InvalidDataException("Mesh must contain fewer than 300000 triangles.");
            var points=new float[indices.Length*3];var normals=new float[points.Length];var uvs=new float[indices.Length*2];
            for(int i=0;i<indices.Length;i++)
            {
                int v=indices[i];if(v<0||v>=vertexCount)throw new InvalidDataException("Mesh index out of range.");
                var orig=new Vector4(pos[v*3],pos[v*3+1],pos[v*3+2],1);
                float x=orig.X*transform[0]+orig.Y*transform[4]+orig.Z*transform[8]+transform[12];
                float y=orig.X*transform[1]+orig.Y*transform[5]+orig.Z*transform[9]+transform[13];
                float z=orig.X*transform[2]+orig.Y*transform[6]+orig.Z*transform[10]+transform[14];
                points[i*3]=x;points[i*3+1]=y;points[i*3+2]=z;
                _min[0]=Math.Min(x,_min[0]);_min[1]=Math.Min(y,_min[1]);_min[2]=Math.Min(z,_min[2]);
                _max[0]=Math.Max(x,_max[0]);_max[1]=Math.Max(y,_max[1]);_max[2]=Math.Max(z,_max[2]);
                if (uv!=null){uvs[i*2]=uv[v*2];uvs[i*2+1]=uv[v*2+1];}
                if (normal!=null)
                {
                    float nx=normal[v*3],ny=normal[v*3+1],nz=normal[v*3+2];
                    float rx=nx*transform[0]+ny*transform[4]+nz*transform[8];
                    float ry=nx*transform[1]+ny*transform[5]+nz*transform[9];
                    float rz=nx*transform[2]+ny*transform[6]+nz*transform[10];
                    float inv=1f/Math.Max(.000001f,(float)Math.Sqrt(rx*rx+ry*ry+rz*rz));
                    normals[i*3]=rx*inv;normals[i*3+1]=ry*inv;normals[i*3+2]=rz*inv;
                }
            }
            if(normal==null)
                for(int i=0;i<indices.Length;i+=3)
                {
                    var a=new Vector3(points[i*3],points[i*3+1],points[i*3+2]);
                    var b=new Vector3(points[(i+1)*3],points[(i+1)*3+1],points[(i+1)*3+2]);
                    var c=new Vector3(points[(i+2)*3],points[(i+2)*3+1],points[(i+2)*3+2]);
                    var n=Vector3.Normalize(Vector3.Cross(b-a,c-a));
                    if (!float.IsFinite(n.X))n=Vector3.UnitY;
                    for(int k=0;k<3;k++){normals[(i+k)*3]=n.X;normals[(i+k)*3+1]=n.Y;normals[(i+k)*3+2]=n.Z;}
                }
            _parts.Add(new Part{Positions=Direct(points),Normals=Direct(normals),Uvs=Direct(uvs),
                Count=indices.Length,MaterialIndex=Int(primitive,"material")});
        }

        void Traverse(int nodeIndex,float[] parent,HashSet<int> ancestors)
        {
            if (!ancestors.Add(nodeIndex))throw new InvalidDataException("Circular GLB node tree.");
            var n=nodes[nodeIndex];float[] local=new float[16];GlMatrix.SetIdentityM(local,0);
            if(Has(n,"matrix"))local=Numbers(n,"matrix",local);
            else
            {
                var t=Numbers(n,"translation",new float[]{0,0,0});
                var q=Numbers(n,"rotation",new float[]{0,0,0,1});
                var scale=Numbers(n,"scale",new float[]{1,1,1});
                GlMatrix.TranslateM(local,0,t[0],t[1],t[2]);
                // Quaternion converted to a 4x4 rotation matrix, column-major.
                float x=q[0],y=q[1],z=q[2],w=q[3];
                float[] rot={1-2*y*y-2*z*z,2*x*y+2*z*w,2*x*z-2*y*w,0,
                             2*x*y-2*z*w,1-2*x*x-2*z*z,2*y*z+2*x*w,0,
                             2*x*z+2*y*w,2*y*z-2*x*w,1-2*x*x-2*y*y,0,
                             0,0,0,1};
                var temp=new float[16];GlMatrix.MultiplyMM(temp,0,local,0,rot,0);local=temp;
                GlMatrix.ScaleM(local,0,scale[0],scale[1],scale[2]);
            }
            var world=new float[16];GlMatrix.MultiplyMM(world,0,parent,0,local,0);
            if (Has(n,"skin"))throw new InvalidDataException("Animated/rigged meshes must first be exported as static GLB.");
            if(Has(n,"mesh"))
            {
                var m=meshes[Int(n,"mesh")];
                foreach(var primitive in m.GetProperty("primitives").EnumerateArray())ParsePrimitive(primitive,world);
            }
            if(Has(n,"children"))foreach(var child in n.GetProperty("children").EnumerateArray())Traverse(child.GetInt32(),world,ancestors);
            ancestors.Remove(nodeIndex);
        }
        float[] identity=new float[16];GlMatrix.SetIdentityM(identity,0);
        if (Has(root,"scenes"))
        {
            int index=Int(root,"scene");
            foreach(var n in root.GetProperty("scenes")[index].GetProperty("nodes").EnumerateArray())Traverse(n.GetInt32(),identity,new HashSet<int>());
        }
        else for(int i=0;i<nodes.GetArrayLength();i++) Traverse(i,identity,new HashSet<int>());
    }

    private static int Shader(int type,string source)
    {
        int id=GLES.GlCreateShader(type);GLES.GlShaderSource(id,source);GLES.GlCompileShader(id);
        int[] ok=new int[1];GLES.GlGetShaderiv(id,GLES.GlCompileStatus,ok,0);
        if(ok[0]==0)throw new InvalidOperationException("AR shader compile failed: "+GLES.GlGetShaderInfoLog(id));
        return id;
    }
    public void Initialise()
    {
        const string vs="attribute vec3 aPoint;attribute vec3 aNormal;attribute vec2 aUV;uniform mat4 uMVP;varying vec3 vNormal;varying vec2 vUV;"+
            "void main(){gl_Position=uMVP*vec4(aPoint,1.0);vNormal=normalize(aNormal);vUV=aUV;}";
        const string fs="precision mediump float;varying vec3 vNormal;varying vec2 vUV;uniform sampler2D uTex;uniform vec4 uTint;"+
            "void main(){vec3 l=normalize(vec3(-0.5,0.9,0.75));float diffuse=max(0.0,dot(normalize(vNormal),l));"+
            "vec4 albedo=texture2D(uTex,vec2(vUV.x,1.0-vUV.y))*uTint;gl_FragColor=vec4(albedo.rgb*(0.52+0.48*diffuse),albedo.a);}";
        int v=Shader(GLES.GlVertexShader,vs),f=Shader(GLES.GlFragmentShader,fs);
        _program=GLES.GlCreateProgram();GLES.GlAttachShader(_program,v);GLES.GlAttachShader(_program,f);GLES.GlLinkProgram(_program);
        var linkStatus = new int[1];
        GLES.GlGetProgramiv(_program, GLES.GlLinkStatus, linkStatus, 0);
        if (linkStatus[0] == 0)
            throw new InvalidOperationException("3D wildlife shader link failed: " + GLES.GlGetProgramInfoLog(_program));
        _position=GLES.GlGetAttribLocation(_program,"aPoint");_normal=GLES.GlGetAttribLocation(_program,"aNormal");
        _uv=GLES.GlGetAttribLocation(_program,"aUV");_mvpLoc=GLES.GlGetUniformLocation(_program,"uMVP");
        _colorLoc=GLES.GlGetUniformLocation(_program,"uTint");_textureLoc=GLES.GlGetUniformLocation(_program,"uTex");
        int[] ids=new int[1];GLES.GlGenTextures(1,ids,0);_whiteTexture=ids[0];
        GLES.GlBindTexture(GLES.GlTexture2d,_whiteTexture);
        GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureMinFilter,GLES.GlLinear);
        GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureMagFilter,GLES.GlLinear);
        ByteBuffer white=ByteBuffer.AllocateDirect(4);white.Put(new byte[]{255,255,255,255});white.Position(0);
        GLES.GlTexImage2D(GLES.GlTexture2d,0,GLES.GlRgba,1,1,0,GLES.GlRgba,GLES.GlUnsignedByte,white);
        foreach(var m in _materials)
        {
            m.GlTexture=_whiteTexture;if(m.Image is null)continue;
            using var bmp=BitmapFactory.DecodeByteArray(m.Image,0,m.Image.Length);
            if(bmp is null)continue;
            GLES.GlGenTextures(1,ids,0);m.GlTexture=ids[0];
            GLES.GlBindTexture(GLES.GlTexture2d,m.GlTexture);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureMinFilter,GLES.GlLinear);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureMagFilter,GLES.GlLinear);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureWrapS,GLES.GlClampToEdge);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureWrapT,GLES.GlClampToEdge);
            GLUtils.TexImage2D(GLES.GlTexture2d,0,bmp,0);
        }
    }

    public void Draw(float[] view,float[] projection,float[] anchor)
    {
        if(_program==0)return;
        float maxExtent=Math.Max(_max[0]-_min[0],Math.Max(_max[1]-_min[1],_max[2]-_min[2]));
        if(maxExtent<=0||!float.IsFinite(maxExtent))return;
        float s=_displaySizeMetres/maxExtent;
        GlMatrix.SetIdentityM(_model,0);
        GlMatrix.TranslateM(_model,0,anchor[0],anchor[1],anchor[2]);
        GlMatrix.ScaleM(_model,0,s,s,s);
        GlMatrix.TranslateM(_model,0,-(_min[0]+_max[0])*.5f,-_min[1],-(_min[2]+_max[2])*.5f);
        GlMatrix.MultiplyMM(_vm,0,view,0,_model,0);GlMatrix.MultiplyMM(_mvp,0,projection,0,_vm,0);
        GLES.GlEnable(GLES.GlDepthTest);GLES.GlDepthMask(true);
        GLES.GlDisable(0x0B44); // GL_CULL_FACE: disable face culling for imported GLB meshes.
        GLES.GlDisable(GLES.GlBlend);
        GLES.GlUseProgram(_program);
        GLES.GlUniformMatrix4fv(_mvpLoc,1,false,_mvp,0);
        GLES.GlActiveTexture(GLES.GlTexture0);GLES.GlUniform1i(_textureLoc,0);
        GLES.GlEnableVertexAttribArray(_position);GLES.GlEnableVertexAttribArray(_normal);GLES.GlEnableVertexAttribArray(_uv);
        foreach(var part in _parts)
        {
            var mat=_materials[Math.Clamp(part.MaterialIndex,0,_materials.Count-1)];
            GLES.GlBindTexture(GLES.GlTexture2d,mat.GlTexture);
            var col=mat.Factor;
            GLES.GlUniform4f(_colorLoc,col[0],col[1],col[2],col[3]);
            part.Positions.Position(0);part.Normals.Position(0);part.Uvs.Position(0);
            GLES.GlVertexAttribPointer(_position,3,GLES.GlFloat,false,0,part.Positions);
            GLES.GlVertexAttribPointer(_normal,3,GLES.GlFloat,false,0,part.Normals);
            GLES.GlVertexAttribPointer(_uv,2,GLES.GlFloat,false,0,part.Uvs);
            GLES.GlDrawArrays(GLES.GlTriangles,0,part.Count);
        }
        GLES.GlDisableVertexAttribArray(_position);GLES.GlDisableVertexAttribArray(_normal);GLES.GlDisableVertexAttribArray(_uv);
        GLES.GlDisable(GLES.GlDepthTest);
    }
}
#endif
