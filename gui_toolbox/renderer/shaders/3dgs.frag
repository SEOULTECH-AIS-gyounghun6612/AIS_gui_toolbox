#version 450 core
precision mediump float;

in vec4 v_color;
in vec2 v_position;
layout(location = 0) out vec4 out_color;

void main () {
  float A = -dot(v_position, v_position);
  if (A < -4.0) discard;
  float B = exp(A) * v_color.a;
  out_color = vec4(B * v_color.rgb, B);
}