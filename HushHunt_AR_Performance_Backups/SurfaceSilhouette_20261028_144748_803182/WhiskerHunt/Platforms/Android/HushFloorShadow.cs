#if ANDROID
using Android.Opengl;
using Java.Nio;
using GLES = Android.Opengl.GLES20;
using GlMatrix = Android.Opengl.Matrix;

namespace WhiskerHunt;

/// <summary>
/// Camera-background contact shadow for HD glTF assets which cannot be parsed
/// by the legacy static-mesh renderer. Compiled on the ARCore OpenGL thread.
/// This is a soft ground decal, not real world-depth occlusion or a Filament
/// shadow-receiving plane. It remains attached to the tracked ARCore anchor.
/// </summary>
internal sealed class HushFloorShadow
{
    private int _program, _vertex, _mvp, _centre, _size, _alpha;
    private FloatBuffer? _quad;
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

    public void Initialise()
    {
        const string vertex = "attribute vec2 aPoint;uniform mat4 uMVP;uniform vec3 uCenter;uniform vec2 uSize;varying vec2 vPoint;" +
            "void main(){vPoint=aPoint;vec3 world=vec3(uCenter.x+aPoint.x*uSize.x,uCenter.y,uCenter.z+aPoint.y*uSize.y);gl_Position=uMVP*vec4(world,1.0);}";
        const string fragment = "precision mediump float;varying vec2 vPoint;uniform float uAlpha;" +
            "void main(){float d=length(vPoint);float f=1.0-smoothstep(0.10,1.0,d);gl_FragColor=vec4(0.0,0.0,0.0,f*uAlpha);}";
        int v = Shader(GLES.GlVertexShader, vertex);
        int f = Shader(GLES.GlFragmentShader, fragment);
        _program = GLES.GlCreateProgram();
        GLES.GlAttachShader(_program,v); GLES.GlAttachShader(_program,f); GLES.GlLinkProgram(_program);
        var ok = new int[1]; GLES.GlGetProgramiv(_program, GLES.GlLinkStatus, ok, 0);
        if (ok[0] == 0) throw new InvalidOperationException("Floor-shadow link: " + GLES.GlGetProgramInfoLog(_program));
        _vertex = GLES.GlGetAttribLocation(_program,"aPoint");
        _mvp = GLES.GlGetUniformLocation(_program,"uMVP");
        _centre = GLES.GlGetUniformLocation(_program,"uCenter");
        _size = GLES.GlGetUniformLocation(_program,"uSize");
        _alpha = GLES.GlGetUniformLocation(_program,"uAlpha");
        _quad = Buffer(new float[] { -1f,-1f, 1f,-1f, -1f,1f, 1f,1f });
    }

    public void Draw(float[] view, float[] projection, float[] anchor, float radius)
    {
        if (_program == 0 || _quad is null) return;
        var pv = new float[16];
        GlMatrix.MultiplyMM(pv,0,projection,0,view,0);
        GLES.GlDisable(GLES.GlDepthTest);
        GLES.GlDepthMask(false);
        GLES.GlEnable(GLES.GlBlend);
        GLES.GlBlendFunc(GLES.GlSrcAlpha,GLES.GlOneMinusSrcAlpha);
        GLES.GlUseProgram(_program);
        GLES.GlUniformMatrix4fv(_mvp,1,false,pv,0);
        GLES.GlUniform3f(_centre,anchor[0],anchor[1]+.0035f,anchor[2]);
        GLES.GlUniform2f(_size,radius,radius*.8f);
        GLES.GlUniform1f(_alpha,.075f);
        _quad.Position(0);
        GLES.GlEnableVertexAttribArray(_vertex);
        GLES.GlVertexAttribPointer(_vertex,2,GLES.GlFloat,false,0,_quad);
        GLES.GlDrawArrays(GLES.GlTriangleStrip,0,4);
        GLES.GlDisableVertexAttribArray(_vertex);
        GLES.GlDisable(GLES.GlBlend);
        GLES.GlDepthMask(true);
    }
}
#endif
