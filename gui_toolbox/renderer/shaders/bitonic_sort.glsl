#version 430 core

// 하나의 작업 그룹에 포함될 스레드 개수
layout(local_size_x = 1024) in;

// 정렬할 데이터의 구조체 정의
struct DepthIndexPair {
    float depth;
    uint original_index;
};

// 입력/출력: 깊이와 인덱스 쌍으로 이루어진 버퍼
layout(std430, binding = 0) buffer PairBuffer {
    DepthIndexPair pairs[];
};

// 파이썬에서 전달받는 정렬 단계 정보
uniform uint stage;
uniform uint sub_stage;

void main() {
    uint id = gl_GlobalInvocationID.x;
    
    // 1. 비교할 다른 요소의 인덱스 계산
    uint other_id = id ^ (1 << sub_stage);

    // 2. 중복 교환을 막기 위해 한쪽 스레드만 작업 수행
    if (other_id > id) {
        // 3. 현재 블록의 정렬 방향 결정 (오름차순 또는 내림차순)
        // id를 stage+1 만큼 오른쪽 시프트한 값의 최하위 비트를 확인
        uint direction = (id >> stage) & 1;

        // 4. 깊이를 비교하고, 정렬 방향에 맞지 않으면 교환
        if (pairs[id].depth > pairs[other_id].depth == bool(direction)) {
            // 구조체 전체를 통째로 교환
            DepthIndexPair temp = pairs[id];
            pairs[id] = pairs[other_id];
            pairs[other_id] = temp;
        }
    }
}