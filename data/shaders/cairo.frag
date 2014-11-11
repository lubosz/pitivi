#version 140
#extension GL_ARB_texture_rectangle : enable

in vec2 out_uv;
uniform sampler2DRect cairoSampler;
out vec4 outColor;

void main()
{
        outColor = texture2DRect (cairoSampler, out_uv);
}