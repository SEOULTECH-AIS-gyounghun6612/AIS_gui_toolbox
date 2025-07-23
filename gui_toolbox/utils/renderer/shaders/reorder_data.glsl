#version 430 core
layout(local_size_x = 1024) in;

// 입력 1 (binding=0): 정렬된 깊이/인덱스 쌍
struct DepthIndexPair { float depth; uint original_index; };
layout(std430, binding = 0) readonly buffer SortedPairs {
    DepthIndexPair sorted_pairs[];
};

// 입력 2 (binding=1): 원본 순서의 interleaved 가우시안 데이터
layout(std430, binding = 1) readonly buffer OriginalGaussianData {
    float g_data_in[];
};

// 출력 (binding=2): 깊이 순으로 재정렬된 가우시안 데이터
layout(std430, binding = 2) writeonly buffer ReorderedGaussianData {
    float g_data_out[];
};

// Uniform 변수: 전체 가우시안 개수와 단일 가우시안의 데이터 길이(stride)
uniform uint num_elements;
uniform int total_dim; // 예: (pos, rot, scale, opacity, color) -> 14

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= num_elements) return;

    // 1. 정렬된 버퍼에서 내가 가져와야 할 데이터의 '원본 위치'를 찾음
    uint original_idx = sorted_pairs[id].original_index;

    // 2. 원본 데이터와 목적지 데이터의 시작 메모리 주소 계산
    int source_start_idx = int(original_idx) * total_dim;
    int dest_start_idx = int(id) * total_dim;

    // 3. total_dim 만큼의 float 데이터를 통째로 복사
    for (int i = 0; i < total_dim; ++i) {
        g_data_out[dest_start_idx + i] = g_data_in[source_start_idx + i];
    }
}