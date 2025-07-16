#version 430 core
layout(local_size_x = 1024) in;

// 입력: 원본 가우시안 위치 데이터
layout(std430, binding = 0) buffer OriginalPositions {
    vec3 positions[];
};

// 출력: 깊이와 인덱스를 저장할 버퍼
layout(std430, binding = 1) buffer DepthIndexPairs {
    float depth;
    uint original_index;
} pairs[];

uniform mat4 view_matrix;

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= positions.length()) return;

    // 카메라 뷰 공간에서의 깊이(z값) 계산
    vec4 pos_view = view_matrix * vec4(positions[id], 1.0);
    
    // 계산된 결과를 출력 버퍼에 저장
    pairs[id].depth = pos_view.z;
    pairs[id].original_index = id;
}