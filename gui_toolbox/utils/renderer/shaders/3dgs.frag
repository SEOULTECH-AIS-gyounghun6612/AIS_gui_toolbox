// Original Source: https://github.com/limacv/GaussianSplattingViewer/blob/main/shaders/gau_frag.glsl
#version 430 core

in vec3 color;
in float alpha;
in vec3 conic;
in vec2 coordxy;

uniform int render_mod; // 0:gaussian, 1:depth, 2:flat, 3:debug

out vec4 FragColor;
void main()
{
    // [변경] render_mod에 따른 최종 모양 결정
    if (render_mod == 3) // 3: debug (billboard)
    {
        FragColor = vec4(color, 1.f);
        return;
    }

    // 공통 계산 (gaussian_ball, flat_ball)
    float power = -0.5f * (conic.x * coordxy.x * coordxy.x + conic.z * coordxy.y * coordxy.y) - conic.y * coordxy.x * coordxy.y;
    if (power > 0.f)
        discard;
    
    float opacity = min(0.99f, alpha * exp(power));
    if (opacity < 1.f / 255.f)
        discard;

    if (render_mod == 2) // 2: flat_ball
    {
        // 알파 값에 임계값을 적용하여 딱딱한 경계를 만듦
        opacity = opacity > 0.22 ? 1.0 : 0.0;
    }
    // render_mod가 0 (gaussian_ball)일 경우, 계산된 opacity를 그대로 사용

    FragColor = vec4(color, opacity);
}