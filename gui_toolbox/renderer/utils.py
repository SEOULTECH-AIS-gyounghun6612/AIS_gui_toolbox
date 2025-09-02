import numpy as np

# PyTorch의 가용성에 따라 동적으로 import 시도
try:
    import torch
    TORCH_AVAILABLE = torch.cuda.is_available()
except ImportError:
    TORCH_AVAILABLE = False

# PyTorch 연산 시 텐서 캐싱을 위한 전역 변수
GAU_ID = None
GAU_XYZ_BUFFER = None

def __Sort_gau(xyz, view, backend):
    """
    백엔드(NumPy/PyTorch)에 독립적인 핵심 가우시안 정렬 로직.
    좌표를 뷰 공간으로 변환하고 깊이 값을 기준으로 정렬 인덱스를 반환합니다.

    Args:
        xyz (array-like): 가우시안의 월드 좌표 (N, 3). (NumPy 배열 또는 PyTorch 텐서)
        view (array-like): 카메라 뷰 매트릭스 (4, 4). (NumPy 배열 또는 PyTorch 텐서)
        backend (module): 연산에 사용할 백엔드 모듈 (numpy 또는 torch).

    Returns:
        array-like: 정렬된 인덱스 배열.
    """
    # 뷰 공간으로 좌표 변환. 브로드캐스팅을 활용합니다.
    _xyz = view[None, :3, :3] @ xyz[..., None] + view[None, :3, 3, None]

    # 백엔드의 argsort 함수를 사용하여 깊이 기준 정렬
    return backend.argsort(_xyz[:, 2, 0])


def Sort_gau_np(xyz: np.ndarray, view: np.ndarray) -> np.ndarray:
    """
    NumPy를 사용하여 가우시안을 정렬하는 래퍼 함수.

    Args:
        xyz (np.ndarray): 가우시안의 월드 좌표 (N, 3).
        view_mat (np.ndarray): 카메라 뷰 매트릭스 (4, 4).

    Returns:
        np.ndarray: 정렬된 인덱스 배열 (N, 1), int32 타입.
    """
    # NumPy 백엔드로 핵심 로직 호출
    return __Sort_gau(xyz, view, np).astype(np.int32).reshape(-1, 1)


def Sort_gau_torch(xyz: np.ndarray, view: np.ndarray, gaus_id: int) -> np.ndarray:
    """
    PyTorch(CUDA)를 사용하여 가우시안을 정렬하는 래퍼 함수.
    성능 향상을 위해 GPU에 텐서를 캐싱하는 구조를 포함합니다.

    Args:
        gaus_xyz (np.ndarray): 가우시안 위치 좌표 (N, 3).
        view_mat (np.ndarray): 카메라 뷰 매트릭스 (4, 4).
        gaus_id (int): 캐싱 확인을 위한 가우시안 데이터 객체의 ID.

    Returns:
        np.ndarray: 정렬된 인덱스 배열 (N, 1), int32 타입.
    """    
    # ID가 다를 경우, 새로운 가우시안 데이터로 간주하고 GPU에 텐서 새로 생성
    if GAU_ID != gaus_id:
        GAU_XYZ_BUFFER = torch.tensor(xyz, device='cuda', dtype=torch.float32)
        GAU_ID = gaus_id

    _xyz_torch = GAU_XYZ_BUFFER
    view_mat_torch = torch.tensor(view, device='cuda', dtype=torch.float32)
    
    # PyTorch 백엔드로 핵심 로직 호출
    index_torch = __Sort_gau(_xyz_torch, view_mat_torch, torch)
    
    # 결과를 CPU의 NumPy 배열로 변환하여 반환
    return index_torch.type(torch.int32).reshape(-1, 1).cpu().numpy()