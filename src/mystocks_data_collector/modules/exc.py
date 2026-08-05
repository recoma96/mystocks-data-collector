class APIClientError(Exception):
    """API 클라이언트 관련 최상위 예외"""
    pass


class APIRequestError(APIClientError):
    """네트워크 오류, 타임아웃 등 요청 전송 자체가 실패했을 때 발생"""

    def __init__(self, message: str, *, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class APIResponseError(APIClientError):
    """응답은 받았으나 HTTP 상태 코드가 에러이거나 파싱이 불가능할 때 발생"""

    def __init__(self, message: str, *, status_code: int, response_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
