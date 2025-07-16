#version 330 core

in vec3 v_color;
in float v_opacity;
in vec2 v_uv;
in mat2 v_conic; // 2D 타원의 형태 (정점 셰이더로부터 받음)

out vec4 FragColor;

void main() {
    // 2D 가우시안 분포 계산 (중심으로부터의 거리)
    float d = dot(v_uv, v_conic * v_uv);

    // 타원의 경계를 벗어나는 픽셀은 그리지 않음 (성능 향상)
    if (d > 1.0) {
        discard;
    }

    // 중심에 가까울수록 불투명하게, 멀수록 투명하게
    float alpha = v_opacity * exp(-0.5 * d);
    
    // 최종 픽셀 색상 출력
    FragColor = vec4(v_color, alpha);
}






