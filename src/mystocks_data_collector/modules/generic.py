from typing import ParamSpec, TypeVar

# 런타임 로직 없이, 데코레이터 등에서 원본 함수의 타입을 보존하기 위한 제네릭 타입 변수 전용 모듈.
# P는 함수의 파라미터 타입들을, T는 반환 타입을 그대로 유지하고 싶을 때 공용으로 사용한다.
P = ParamSpec("P")
T = TypeVar("T")
