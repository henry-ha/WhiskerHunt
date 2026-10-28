#if ANDROID
using Android.Content;
using Android.Graphics;
using Android.Opengl;
using Java.Nio;
using GLES = Android.Opengl.GLES20;
using GlMatrix = Android.Opengl.Matrix;

namespace WhiskerHunt;

/// <summary>
/// ARCore world-anchored, model-specific contact silhouette. The PNG is generated
/// from the model's projected geometry at install time, NOT a generic circle.
/// No second ARCore session or realtime mesh readback; cheap 128x128 alpha texture.
/// </summary>
internal sealed class HushFloorShadow
{
    private int _program, _vertex, _mvp, _centre, _size, _alpha, _rotation, _maskSampler, _useMask, _texture;
    private FloatBuffer? _quad;
    private readonly float[] _pv = new float[16];
    private static FloatBuffer Buffer(float[] values)
    {
        var b = ByteBuffer.AllocateDirect(values.Length * 4).Order(ByteOrder.NativeOrder()).AsFloatBuffer();
        b.Put(values); b.Position(0); return b;
    }
    private static int Shader(int kind, string source)
    {
        int id = GLES.GlCreateShader(kind);
        GLES.GlShaderSource(id, source); GLES.GlCompileShader(id);
        var ok = new int[1]; GLES.GlGetShaderiv(id, GLES.GlCompileStatus, ok, 0);
        if (ok[0] == 0) throw new InvalidOperationException("Floor-shadow shader: " + GLES.GlGetShaderInfoLog(id));
        return id;
    }
    public void Initialise(Context context, string? assetName)
    {
        const string vertex = "attribute vec2 aPoint;uniform mat4 uMVP;uniform vec3 uCenter;uniform vec2 uSize;uniform float uAngle;varying vec2 vPoint;" +
            "void main(){vPoint=aPoint;float c=cos(uAngle),s=sin(uAngle);vec2 p=vec2(c*aPoint.x+s*aPoint.y,-s*aPoint.x+c*aPoint.y);" +
            "vec3 world=vec3(uCenter.x+p.x*uSize.x,uCenter.y,uCenter.z+p.y*uSize.y);gl_Position=uMVP*vec4(world,1.0);}";
        const string fragment = "precision mediump float;varying vec2 vPoint;uniform float uAlpha;uniform float uUseMask;uniform sampler2D uMask;" +
            "void main(){float falloff=1.0-smoothstep(0.10,1.0,length(vPoint));" +
            "float silhouette=texture2D(uMask,clamp(vPoint*0.5+0.5,0.0,1.0)).a;" +
            "float opacity=mix(falloff,silhouette,uUseMask);gl_FragColor=vec4(0.0,0.0,0.0,opacity*uAlpha);}";
        int v = Shader(GLES.GlVertexShader, vertex), f = Shader(GLES.GlFragmentShader, fragment);
        _program = GLES.GlCreateProgram();
        GLES.GlAttachShader(_program,v); GLES.GlAttachShader(_program,f); GLES.GlLinkProgram(_program);
        var ok = new int[1]; GLES.GlGetProgramiv(_program, GLES.GlLinkStatus, ok, 0);
        GLES.GlDeleteShader(v); GLES.GlDeleteShader(f);
        if (ok[0] == 0) throw new InvalidOperationException("Floor-shadow link: " + GLES.GlGetProgramInfoLog(_program));
        _vertex = GLES.GlGetAttribLocation(_program,"aPoint");
        _mvp = GLES.GlGetUniformLocation(_program,"uMVP");
        _centre = GLES.GlGetUniformLocation(_program,"uCenter");
        _size = GLES.GlGetUniformLocation(_program,"uSize");
        _alpha = GLES.GlGetUniformLocation(_program,"uAlpha");
        _rotation = GLES.GlGetUniformLocation(_program,"uAngle");
        _maskSampler = GLES.GlGetUniformLocation(_program,"uMask");
        _useMask = GLES.GlGetUniformLocation(_program,"uUseMask");
        _quad = Buffer(new float[] { -1f,-1f, 1f,-1f, -1f,1f, 1f,1f });
        // Models with unsupported mesh compression retain the safe original blob.
        if (assetName is null || !assetName.EndsWith(".glb",StringComparison.OrdinalIgnoreCase)) return;
        string file = "ar_shadows/" + assetName[..^4] + ".png";
        try
        {
            using var stream = context.Assets!.Open(file);
            using var bitmap = BitmapFactory.DecodeStream(stream);
            if (bitmap is null) throw new InvalidDataException("Shadow PNG failed to decode: " + file);
            var ids = new int[1]; GLES.GlGenTextures(1,ids,0); _texture=ids[0];
            GLES.GlBindTexture(GLES.GlTexture2d,_texture);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureMinFilter,GLES.GlLinear);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureMagFilter,GLES.GlLinear);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureWrapS,GLES.GlClampToEdge);
            GLES.GlTexParameteri(GLES.GlTexture2d,GLES.GlTextureWrapT,GLES.GlClampToEdge);
            GLUtils.TexImage2D(GLES.GlTexture2d,0,bitmap,0);
            GLES.GlBindTexture(GLES.GlTexture2d,0);
        }
        catch (Exception e)
        {
            Android.Util.Log.Warn("HushHuntAR","Shadow silhouette missing; using original contact cue: " + e.Message);
            _texture=0;
        }
    }
    public void Draw(float[] view, float[] projection, float[] anchor, float radius, float yawDegrees)
    {
        if (_program == 0 || _quad is null) return;
        GlMatrix.MultiplyMM(_pv,0,projection,0,view,0);
        GLES.GlDisable(GLES.GlDepthTest);
        GLES.GlDepthMask(false);
        GLES.GlEnable(GLES.GlBlend);
        GLES.GlBlendFunc(GLES.GlSrcAlpha,GLES.GlOneMinusSrcAlpha);
        GLES.GlUseProgram(_program);
        GLES.GlUniformMatrix4fv(_mvp,1,false,_pv,0);
        GLES.GlUniform3f(_centre,anchor[0],anchor[1]+.004f,anchor[2]);
        GLES.GlUniform2f(_size,radius,radius);
        GLES.GlUniform1f(_rotation,yawDegrees*(MathF.PI/180f));
        GLES.GlUniform1f(_alpha,_texture!=0? .29f : .18f);
        GLES.GlUniform1f(_useMask,_texture!=0?1f:0f);
        GLES.GlActiveTexture(GLES.GlTexture0);
        GLES.GlBindTexture(GLES.GlTexture2d,_texture);
        GLES.GlUniform1i(_maskSampler,0);
        _quad.Position(0);
        GLES.GlEnableVertexAttribArray(_vertex);
        GLES.GlVertexAttribPointer(_vertex,2,GLES.GlFloat,false,0,_quad);
        GLES.GlDrawArrays(GLES.GlTriangleStrip,0,4);
        GLES.GlDisableVertexAttribArray(_vertex);
        GLES.GlBindTexture(GLES.GlTexture2d,0);
        GLES.GlDisable(GLES.GlBlend);
        GLES.GlDepthMask(true);
    }
    public void Release()
    {
        if (_texture!=0) { GLES.GlDeleteTextures(1,new[]{_texture},0);_texture=0; }
        if (_program!=0){GLES.GlDeleteProgram(_program);_program=0;}
    }
}
#endif
