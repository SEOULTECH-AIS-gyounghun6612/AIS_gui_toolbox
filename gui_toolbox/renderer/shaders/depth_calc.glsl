#version 430 core
layout(local_size_x = 1024) in;

// 입력 버퍼(binding=0): 모든 속성이 합쳐진 단일 float 배열
layout(std430, binding = 0) buffer GaussianBuffer {
    float g_data[];
};

// 출력 버퍼(binding=1): 깊이와 인덱스 쌍
struct DepthIndexPair {
    float depth;
    uint original_index;
};
layout(std430, binding = 1) buffer DepthIndexBuffer {
    DepthIndexPair pairs[];
};

uniform mat4 view;
uniform uint num_elements;
// [추가] 단일 가우시안 데이터의 총 float 개수 (Stride)
uniform int total_dim;

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= num_elements) return;

    // Stride를 이용해 현재 가우시안 데이터의 시작 인덱스 계산
    int start_idx = int(id) * total_dim;
    
    // 시작 인덱스에서 위치(vec3) 값을 읽어옴
    vec3 pos = vec3(g_data[start_idx],
                    g_data[start_idx + 1],
                    g_data[start_idx + 2]);

    // 카메라 뷰 공간에서의 깊이(z값) 계산
    vec4 pos_view = view * vec4(pos, 1.0);
    
    // 계산된 결과를 출력 버퍼에 저장
    pairs[id].depth = pos_view.z;
    pairs[id].original_index = id;
}