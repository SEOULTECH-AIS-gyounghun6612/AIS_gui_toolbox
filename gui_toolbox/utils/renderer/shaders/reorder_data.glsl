#version 430 core
layout(local_size_x = 1024) in;

// 1. 정렬된 깊이/인덱스 쌍 (읽기 전용)
struct DepthIndexPair { float depth; uint original_index; };
layout(std430, binding = 0) readonly buffer SortedPairs { 
    DepthIndexPair sorted_pairs[]; 
};

// 2. 재정렬할 모든 속성 버퍼들 (읽기/쓰기 모두 가능)
layout(std430, binding = 1) buffer Positions { vec3 positions[]; };
layout(std430, binding = 2) buffer Colors { vec3 colors[]; };
layout(std430, binding = 3) buffer Opacities { float opacities[]; };
layout(std430, binding = 4) buffer Scales { vec3 scales[]; };
layout(std430, binding = 5) buffer Rotations { vec4 rotations[]; };

uniform uint num_elements;

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= num_elements) return;

    // 3. 정렬된 인덱스 버퍼에서 내가 가져와야 할 데이터의 원래 위치를 찾음
    uint original_idx = sorted_pairs[id].original_index;

    // 4. 원래 위치의 데이터를 임시 변수에 복사
    vec3 temp_pos = positions[original_idx];
    vec3 temp_color = colors[original_idx];
    float temp_opacity = opacities[original_idx];
    vec3 temp_scale = scales[original_idx];
    vec4 temp_rotation = rotations[original_idx];

    // 5. 메모리 장벽: 모든 스레드가 읽기를 마칠 때까지 대기
    // (같은 버퍼에 읽고 쓰므로 race condition 방지를 위해 필요)
    memoryBarrierBuffer();

    // 6. 현재 내 위치(id)에 정렬된 데이터를 덮어씀
    positions[id] = temp_pos;
    colors[id] = temp_color;
    opacities[id] = temp_opacity;
    scales[id] = temp_scale;
    rotations[id] = temp_rotation;
}