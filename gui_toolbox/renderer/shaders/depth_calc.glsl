#version 430 core
layout(local_size_x = 1024) in;

struct Splat {
  vec3 center;
  float alpha;
  vec3 covA;
  vec3 covB;
  vec3 sh[16];
};

layout(std430, binding = 0) readonly buffer SplatBuffer {
    Splat splats[];
};

struct SortElement {
    float depth;
    uint index;
};

layout(std430, binding = 1) writeonly buffer SortBuffer {
    SortElement sort_data[];
};

uniform mat4 view;
uniform uint num_elements;

void main() {
    uint index = gl_GlobalInvocationID.x;
    if (index >= num_elements) {
        return;
    }

    Splat s = splats[index];
    vec4 view_pos = view * vec4(s.center, 1.0);
    
    sort_data[index].depth = view_pos.z;
    sort_data[index].index = index;
}
