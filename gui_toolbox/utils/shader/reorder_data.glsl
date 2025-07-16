#version 430 core
layout(local_size_x = 1024) in;

// 입력 1: 원본 가우시안 데이터 버퍼들
layout(std430, binding = 0) buffer UnsortedPositions { vec3 unsorted_pos[]; };
layout(std430, binding = 1) buffer UnsortedColors { vec3 unsorted_color[]; };
// ... (scales, quats, opacities 등)

// 입력 2: 정렬된 인덱스 버퍼
layout(std430, binding = 5) buffer SortedIndices { uint sorted_idx[]; };


// 출력: 최종 렌더링에 사용될, 정렬된 데이터 버퍼들
layout(std430, binding = 6) buffer SortedPositions { vec3 sorted_pos[]; };
layout(std430, binding = 7) buffer SortedColors { vec3 sorted_color[]; };
// ...

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= sorted_idx.length()) return;

    // 정렬된 순서에 맞는 원래 인덱스를 가져옴
    uint original_index = sorted_idx[id];

    // 원래 인덱스를 사용하여 원본 데이터 버퍼에서 값을 읽어와
    // 새로운 정렬된 버퍼에 순서대로 씀
    sorted_pos[id] = unsorted_pos[original_index];
    sorted_color[id] = unsorted_color[original_index];
    // ... (다른 속성들도 동일하게 복사)
}