#version 430 core
layout(local_size_x = 1024) in;

struct Splat {
  vec3 center;
  float alpha;
  vec3 covA;
  vec3 covB;
  vec3 sh[16];
};

struct SortElement {
    float depth;
    uint index;
};

layout(std430, binding = 0) readonly buffer SortedBuffer {
    SortElement sorted_elements[];
};

layout(std430, binding = 1) readonly buffer OriginalSplatBuffer {
    Splat original_splats[];
};

layout(std430, binding = 2) writeonly buffer ReorderedSplatBuffer {
    Splat reordered_splats[];
};

uniform uint num_elements;

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= num_elements) {
        return;
    }

    uint original_index = sorted_elements[id].index;
    reordered_splats[id] = original_splats[original_index];
}
