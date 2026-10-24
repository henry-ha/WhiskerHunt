#if ANDROID
using Android.Opengl;
using Java.Nio;
using System;
using System.Collections.Generic;
using GLES = Android.Opengl.GLES20;

namespace WhiskerHunt;

/// <summary>
/// Small offline low-poly wildlife models for native ARCore mode. Geometry is
/// genuinely three dimensional (not a sprite / billboard): moving around the
/// ARCore anchor reveals different sides. These are simple family prototypes,
/// not species-accurate photorealistic models.
/// Rendered entirely on-device with OpenGL ES 2.0.
/// </summary>
internal sealed class HushAnimal3D
{
    private int _program, _position, _normal, _mvpUniform, _colorUniform;
    private FloatBuffer? _spherePoints, _sphereNormals;
    private int _sphereVertexCount;
    private readonly float[] _model = new float[16];
    private readonly float[] _viewModel = new float[16];
    private readonly float[] _mvp = new float[16];
    private float[] _view = new float[16], _projection = new float[16];
    private float _ox, _oy, _oz;

    private static FloatBuffer Buffer(float[] data)
    {
        var b = ByteBuffer.AllocateDirect(data.Length * 4)
            .Order(ByteOrder.NativeOrder()).AsFloatBuffer();
        b.Put(data); b.Position(0); return b;
    }
    private static int Shader(int type, string code)
    {
        int result = GLES.GlCreateShader(type);
        GLES.GlShaderSource(result, code);
        GLES.GlCompileShader(result);
        return result;
    }

    public void Initialise()
    {
        const string vertex = "attribute vec3 aPoint;attribute vec3 aNormal;uniform mat4 uMVP;varying float vLight;" +
            "void main(){gl_Position=uMVP*vec4(aPoint,1.);" +
            "vLight=0.46+0.54*max(0.,dot(normalize(aNormal),normalize(vec3(-.4,.8,.7))));}";
        const string fragment = "precision mediump float;varying float vLight;uniform vec4 uColor;" +
            "void main(){gl_FragColor=vec4(uColor.rgb*vLight,uColor.a);}";
        int v = Shader(GLES.GlVertexShader, vertex), f = Shader(GLES.GlFragmentShader, fragment);
        _program = GLES.GlCreateProgram();
        GLES.GlAttachShader(_program, v); GLES.GlAttachShader(_program, f);
        GLES.GlLinkProgram(_program);
        _position = GLES.GlGetAttribLocation(_program, "aPoint");
        _normal = GLES.GlGetAttribLocation(_program, "aNormal");
        _mvpUniform = GLES.GlGetUniformLocation(_program, "uMVP");
        _colorUniform = GLES.GlGetUniformLocation(_program, "uColor");
        // A sphere mesh reused for body, head, feet, ears and tail. Scale and
        // place independent 3D volumes; never stretch a 2D photograph.
        var values = new List<float>();
        const int sectors = 18, stacks = 12;
        for (int ring = 0; ring < stacks; ring++)
        for (int sector = 0; sector < sectors; sector++)
        {
            AddSpherePoint(values, ring, sector, stacks, sectors);
            AddSpherePoint(values, ring + 1, sector, stacks, sectors);
            AddSpherePoint(values, ring + 1, sector + 1, stacks, sectors);
            AddSpherePoint(values, ring, sector, stacks, sectors);
            AddSpherePoint(values, ring + 1, sector + 1, stacks, sectors);
            AddSpherePoint(values, ring, sector + 1, stacks, sectors);
        }
        _sphereVertexCount = values.Count / 3;
        _spherePoints = Buffer(values.ToArray());
        _sphereNormals = Buffer(values.ToArray());
    }
    private static void AddSpherePoint(List<float> coords, int ring, int sector, int stacks, int sectors)
    {
        float phi = (float)(Math.PI * ring / stacks);
        float theta = (float)(2 * Math.PI * sector / sectors);
        coords.Add((float)(Math.Sin(phi) * Math.Cos(theta)));
        coords.Add((float)Math.Cos(phi));
        coords.Add((float)(Math.Sin(phi) * Math.Sin(theta)));
    }

    private void Ellipsoid(float x, float y, float z, float sx, float sy, float sz,
        float r, float g, float b)
    {
        Matrix.SetIdentityM(_model, 0);
        Matrix.TranslateM(_model, 0, _ox+x, _oy+y, _oz+z);
        Matrix.ScaleM(_model, 0, sx, sy, sz);
        Matrix.MultiplyMM(_viewModel, 0, _view, 0, _model, 0);
        Matrix.MultiplyMM(_mvp, 0, _projection, 0, _viewModel, 0);
        GLES.GlUniformMatrix4fv(_mvpUniform, 1, false, _mvp, 0);
        GLES.GlUniform4f(_colorUniform, r, g, b, 1f);
        _spherePoints!.Position(0); _sphereNormals!.Position(0);
        GLES.GlVertexAttribPointer(_position, 3, GLES.GlFloat, false, 0, _spherePoints);
        GLES.GlVertexAttribPointer(_normal, 3, GLES.GlFloat, false, 0, _sphereNormals);
        GLES.GlDrawArrays(GLES.GlTriangles, 0, _sphereVertexCount);
    }

    private void PairEyes(float x, float y, float z, float side = .077f)
    {
        Ellipsoid(x-side,y,z,.016f,.019f,.014f,.08f,.06f,.04f);
        Ellipsoid(x+side,y,z,.016f,.019f,.014f,.08f,.06f,.04f);
    }

    public void Draw(float[] view, float[] projection, float[] anchor, string group, string name)
    {
        if (_program == 0 || _spherePoints is null) return;
        _view=view; _projection=projection;
        _ox=anchor[0];_oy=anchor[1];_oz=anchor[2];
        GLES.GlEnable(GLES.GlDepthTest);
        GLES.GlDepthMask(true);
        GLES.GlClear(GLES.GlDepthBufferBit);
        GLES.GlUseProgram(_program);
        GLES.GlEnableVertexAttribArray(_position);
        GLES.GlEnableVertexAttribArray(_normal);
        var type=group.ToLowerInvariant();
        var species=name.ToLowerInvariant();
        if (type == "bird")
        {
            bool swan=species.Contains("swan");
            float white=swan ? .95f : .64f;
            Ellipsoid(0,.18f,0,.32f,.18f,.23f,white,white,.89f);
            // 3D wings and back are visible from any direction, unlike the 2D sprite.
            Ellipsoid(-.19f,.23f,0,.16f,.09f,.17f,white*.9f,white*.9f,white*.87f);
            Ellipsoid(.19f,.23f,0,.16f,.09f,.17f,white*.9f,white*.9f,white*.87f);
            if(swan)
            {
                Ellipsoid(.20f,.34f,.12f,.073f,.21f,.074f,.96f,.95f,.92f);
                Ellipsoid(.22f,.53f,.10f,.085f,.095f,.085f,.97f,.96f,.93f);
                Ellipsoid(.22f,.51f,.20f,.058f,.025f,.09f,.96f,.43f,.12f);
                PairEyes(.22f,.56f,.175f,.06f);
            }
            else
            {
                Ellipsoid(0,.30f,.22f,.13f,.13f,.13f,.70f,.49f,.30f);
                Ellipsoid(0,.28f,.35f,.075f,.04f,.09f,.9f,.65f,.19f);
                PairEyes(0,.34f,.32f);
            }
        }
        else if(type=="squirrel" || type=="rabbit" || type=="cat" || type=="dog" || type=="hedgehog")
        {
            float r=type=="squirrel" ? .55f : .70f,g=type=="squirrel" ? .47f : .48f,b=.33f;
            Ellipsoid(0,.24f,0,.25f,.19f,.22f,r,g,b);
            Ellipsoid(0,.40f,.21f,.17f,.15f,.16f,r+.05f,g+.04f,b+.04f);
            Ellipsoid(-.15f,.095f,.18f,.075f,.11f,.085f,r,g,b);
            Ellipsoid(.15f,.095f,.18f,.075f,.11f,.085f,r,g,b);
            Ellipsoid(-.14f,.10f,-.15f,.065f,.11f,.08f,r,g,b);
            Ellipsoid(.14f,.10f,-.15f,.065f,.11f,.08f,r,g,b);
            if(type=="squirrel")
            {
                Ellipsoid(0,.40f,-.29f,.14f,.30f,.13f,r+.12f,g+.10f,b+.08f);
                Ellipsoid(0,.58f,-.36f,.15f,.24f,.14f,r+.12f,g+.10f,b+.08f);
            }
            else if(type=="rabbit")
            {
                Ellipsoid(-.10f,.66f,.19f,.065f,.25f,.055f,r,g,b);
                Ellipsoid(.10f,.66f,.19f,.065f,.25f,.055f,r,g,b);
            }
            else
            {
                Ellipsoid(-.12f,.52f,.19f,.065f,.12f,.075f,r,g,b);
                Ellipsoid(.12f,.52f,.19f,.065f,.12f,.075f,r,g,b);
            }
            Ellipsoid(0,.37f,.35f,.11f,.085f,.10f,.87f,.79f,.67f);
            Ellipsoid(0,.39f,.44f,.026f,.025f,.02f,.14f,.11f,.11f);
            PairEyes(0,.45f,.34f,.13f);
        }
        else if(type=="frog")
        {
            Ellipsoid(0,.16f,0,.29f,.12f,.23f,.26f,.65f,.19f);
            Ellipsoid(0,.21f,.20f,.25f,.12f,.14f,.35f,.75f,.21f);
            Ellipsoid(-.16f,.31f,.28f,.075f,.077f,.071f,.38f,.83f,.27f);
            Ellipsoid(.16f,.31f,.28f,.075f,.077f,.071f,.38f,.83f,.27f);
            PairEyes(0,.33f,.34f,.16f);
            Ellipsoid(-.26f,.08f,-.16f,.14f,.065f,.18f,.27f,.68f,.16f);
            Ellipsoid(.26f,.08f,-.16f,.14f,.065f,.18f,.27f,.68f,.16f);
        }
        else if(type=="snail")
        {
            Ellipsoid(0,.075f,0,.30f,.075f,.18f,.62f,.50f,.38f);
            Ellipsoid(0,.22f,-.08f,.21f,.20f,.15f,.68f,.52f,.25f);
            Ellipsoid(0,.23f,.23f,.08f,.17f,.075f,.59f,.50f,.36f);
            Ellipsoid(-.07f,.40f,.23f,.028f,.05f,.028f,.58f,.48f,.34f);
            Ellipsoid(.07f,.40f,.23f,.028f,.05f,.028f,.58f,.48f,.34f);
        }
        else if(type=="butterfly" || type=="moth")
        {
            Ellipsoid(0,.25f,0,.055f,.19f,.055f,.33f,.25f,.20f);
            Ellipsoid(-.21f,.30f,0,.19f,.24f,.05f,.88f,.42f,.14f);
            Ellipsoid(.21f,.30f,0,.19f,.24f,.05f,.88f,.42f,.14f);
            Ellipsoid(-.19f,.11f,0,.15f,.13f,.05f,.82f,.34f,.12f);
            Ellipsoid(.19f,.11f,0,.15f,.13f,.05f,.82f,.34f,.12f);
        }
        else
        {
            // Honest low-poly 3D fallback for uncatalogued families.
            Ellipsoid(0,.20f,0,.24f,.18f,.25f,.58f,.62f,.46f);
            Ellipsoid(0,.35f,.23f,.15f,.14f,.14f,.65f,.66f,.49f);
            PairEyes(0,.39f,.35f);
            Ellipsoid(-.14f,.10f,-.17f,.06f,.11f,.07f,.52f,.56f,.38f);
            Ellipsoid(.14f,.10f,-.17f,.06f,.11f,.07f,.52f,.56f,.38f);
        }
        GLES.GlDisableVertexAttribArray(_position);
        GLES.GlDisableVertexAttribArray(_normal);
        GLES.GlDisable(GLES.GlDepthTest);
    }
}
#endif
