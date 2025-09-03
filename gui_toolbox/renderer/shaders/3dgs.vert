#version 450 core
precision mediump float;

layout (location = 0) in vec2 in_position;

// UNIFORMS
uniform mat4 u_projection_matrix;
uniform mat4 u_view_matrix;
uniform vec2 u_focal;
uniform vec2 u_viewport;
// uniform vec3 u_cam_pos;
// uniform int u_sh_degree;

struct Splat {
  vec3 center;
  float alpha;
  vec3 covA;
  vec3 covB;
  vec3 sh[16];
};

layout(std430, binding = 0) readonly buffer splat_buffer {
  Splat splats[];
};


out vec4 v_color;
out vec2 v_position;

mat3 transpose(mat3 m) {
  return mat3(
      m[0][0], m[1][0], m[2][0],
      m[0][1], m[1][1], m[2][1],
      m[0][2], m[1][2], m[2][2]
  );
}


const float SH_C0 = 0.28209479177387814;
const float SH_C1 = 0.4886025119029199;
const float SH_C2[5] = float[5](
  1.0925484305920792,
  -1.0925484305920792,
  0.31539156525252005,
  -1.0925484305920792,
  0.5462742152960396
);
const float SH_C3[7] = float[7](
  -0.5900435899266435,
  2.890611442640554,
  -0.4570457994644658,
  0.3731763325901154,
  -0.4570457994644658,
  1.445305721320277,
  -0.5900435899266435
);

vec3 get_rgb(vec3 ray_direction) {
    vec3 rgb = vec3(0.5);
    int sh_degree = 0;
    const Splat s = splats[gl_InstanceID];

    rgb += SH_C0 * s.sh[0];

    if (sh_degree >= 1) {
        rgb +=
            - SH_C1 * ray_direction.y * s.sh[1]
            + SH_C1 * ray_direction.z * s.sh[2]
            - SH_C1 * ray_direction.x * s.sh[3];
    }

    if (sh_degree >= 2) {
        float xx = ray_direction.x * ray_direction.x;
        float yy = ray_direction.y * ray_direction.y;
        float zz = ray_direction.z * ray_direction.z;
        float xy = ray_direction.x * ray_direction.y;
        float yz = ray_direction.y * ray_direction.z;
        float xz = ray_direction.x * ray_direction.z;
        rgb +=
            SH_C2[0] * xy * s.sh[4] +
            SH_C2[1] * yz * s.sh[5] +
            SH_C2[2] * (2.0 * zz - xx - yy) * s.sh[6] +
            SH_C2[3] * xz * s.sh[7] +
            SH_C2[4] * (xx - yy) * s.sh[8];

        if (sh_degree >= 3) {
            rgb +=
                SH_C3[0] * ray_direction.y * (3.0 * xx - yy) * s.sh[9] +
                SH_C3[1] * ray_direction.z * xy * s.sh[10] +
                SH_C3[2] * ray_direction.y * (4.0 * zz - xx - yy) * s.sh[11] +
                SH_C3[3] * ray_direction.z * (2.0 * zz - 3.0 * xx - 3.0 * yy) * s.sh[12] +
                SH_C3[4] * ray_direction.x * (4.0 * zz - xx - yy) * s.sh[13] +
                SH_C3[5] * ray_direction.z * (xx - yy) * s.sh[14] +
                SH_C3[6] * ray_direction.x * (xx - 3.0 * yy) * s.sh[15];
        }
    }

    return clamp(rgb, 0.0, 1.0);
}

void main () {
  const Splat s = splats[gl_InstanceID];
  vec4 camspace = u_view_matrix * vec4(s.center, 1);
  vec4 pos2d = u_projection_matrix * camspace;

  float bounds = 1.2 * pos2d.w;
  if (pos2d.z < -pos2d.w
      || pos2d.x < -bounds
      || pos2d.x > bounds
      || pos2d.y < -bounds
      || pos2d.y > bounds) {
      gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
      return;
  }

  mat3 Vrk = mat3(
      s.covA.x, s.covA.y, s.covA.z,
      s.covA.y, s.covB.x, s.covB.y,
      s.covA.z, s.covB.y, s.covB.z
  );

  mat3 J = mat3(
      u_focal.x / camspace.z, 0., -(u_focal.x * camspace.x) / (camspace.z * camspace.z),
      0., -u_focal.y / camspace.z, (u_focal.y * camspace.y) / (camspace.z * camspace.z),
      0., 0., 0.
  );

  mat3 W = transpose(mat3(u_view_matrix));
  mat3 T = W * J;
  mat3 cov = transpose(T) * Vrk * T;

  vec2 vCenter = vec2(pos2d) / pos2d.w;

  float diagonal1 = cov[0][0] + 0.3;
  float offDiagonal = cov[0][1];
  float diagonal2 = cov[1][1] + 0.3;

  float mid = 0.5 * (diagonal1 + diagonal2);
  float radius = length(vec2((diagonal1 - diagonal2) / 2.0, offDiagonal));
  float lambda1 = mid + radius;
  float lambda2 = max(mid - radius, 0.1);
  vec2 diagonalVector = normalize(vec2(offDiagonal, lambda1 - diagonal1));
  vec2 v1 = min(sqrt(2.0 * lambda1), 1024.0) * diagonalVector;
  vec2 v2 = min(sqrt(2.0 * lambda2), 1024.0) * vec2(diagonalVector.y, -diagonalVector.x);

  vec3 u_cam_pos = -u_view_matrix[3].xyz * mat3(u_view_matrix);
  vec3 ray_direction = normalize(s.center - u_cam_pos);
  v_color.rgb = get_rgb(ray_direction);
  v_color.a = s.alpha;
  v_position = in_position;

  gl_Position = vec4(
      vCenter
          + in_position.x * v1 / u_viewport * 2.0
          + in_position.y * v2 / u_viewport * 2.0, 0.0, 1.0);

}