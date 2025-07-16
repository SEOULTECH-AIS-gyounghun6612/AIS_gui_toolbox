#version 330 core

// 입력: 각 가우시안의 속성
layout (location = 0) in vec3 a_center_world; // 가우시안의 월드 좌표계 중심
layout (location = 1) in vec3 a_color;      // 색상 (Spherical Harmonics의 기본값)
layout (location = 2) in float a_opacity;
layout (location = 3) in vec3 a_scale;
layout (location = 4) in vec4 a_quat;       // 회전 (쿼터니언)

// 유니폼: 모든 정점에 동일하게 적용
uniform mat4 view_matrix;
uniform mat4 projection_matrix;
uniform vec2 focal_length; // 카메라의 초점 거리 (fx, fy)

// 출력: 프래그먼트 셰이더로 전달될 데이터
out vec3 v_color;
out float v_opacity;
out vec2 v_uv;
out mat2 v_conic; // 2D 타원의 형태를 결정하는 행렬

// 쿼터니언을 3x3 회전 행렬로 변환하는 함수
mat3 quat_to_mat(vec4 q) {
    float x=q.x, y=q.y, z=q.z, w=q.w;
    return mat3(1.0 - 2.0*(y*y + z*z), 2.0*(x*y - z*w), 2.0*(x*z + y*w),
                2.0*(x*y + z*w), 1.0 - 2.0*(x*x + z*z), 2.0*(y*z - x*w),
                2.0*(x*z - y*w), 2.0*(y*z + x*w), 1.0 - 2.0*(x*x + y*y));
}

void main() {
    v_color = a_color;
    v_opacity = a_opacity;

    // 1. 월드 좌표계의 중심점을 뷰 좌표계로 변환
    vec4 center_view = view_matrix * vec4(a_center_world, 1.0);
    float T_z = center_view.z;

    // 2. 3D 공분산(Covariance) 계산
    mat3 R = quat_to_mat(a_quat);
    mat3 S = mat3(a_scale.x, 0, 0, 0, a_scale.y, 0, 0, 0, a_scale.z);
    mat3 Sigma = transpose(R) * S * S * R;

    // 3. 뷰 변환 행렬에서 회전 부분만 추출
    mat3 W = mat3(view_matrix);
    // 4. 뷰 공간에서의 3D 공분산 계산
    mat3 Cov_view = transpose(W) * Sigma * W;

    // 5. 2D 화면에 투영된 공분산 계산
    mat2 Cov2D = mat2(
        Cov_view[0][0] + 0.3, Cov_view[0][1],
        Cov_view[1][0], Cov_view[1][1] + 0.3
    );
    v_conic = inverse(Cov2D); // 프래그먼트 셰이더에서 사용될 2차 형식 행렬

    // 6. 화면에 그려질 사각형(빌보드)의 크기 결정
    float det = determinant(Cov2D);
    if (det == 0.0) return;
    float radius = 3.0 * sqrt(abs(det)); // 타원을 덮을 수 있는 반지름 계산
    
    // 7. gl_VertexID를 이용해 사각형의 4개 모서리 생성
    vec2 corners[4] = vec2[4](vec2(-1, -1), vec2(1, -1), vec2(-1, 1), vec2(1, 1));
    vec2 corner = corners[gl_VertexID];
    v_uv = corner; // UV 좌표 전달

    // 8. 최종 정점 위치 계산 (뷰 공간 중심점에서 코너 방향으로 이동 후 투영)
    vec2 offset = corner * radius;
    center_view.xy += offset * focal_length / T_z;
    gl_Position = projection_matrix * center_view;
}