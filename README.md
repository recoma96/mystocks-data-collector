# mystocks-data-collector
본인 투자 관련 데이터 수집기


## How To Use

### Installation

이 프로젝트는 [uv](https://docs.astral.sh/uv/)로 의존성을 관리합니다. Python 3.14 이상이 필요합니다 (uv가 자동으로 설치/관리합니다).

```shell
# uv 설치 (아직 설치하지 않았다면)
$ curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
$ powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

# 의존성 설치 (가상환경은 .venv 에 자동 생성됨)
$ uv sync
```

### Run in Dev

```shell
# handler()를 실행하는 개발용 엔트리포인트
$ uv run exec-dev
```

`exec-dev`는 [pyproject.toml](pyproject.toml)의 `[project.scripts]`에 정의되어 있으며, [src/mystocks_data_collector/__init__.py](src/mystocks_data_collector/__init__.py)의 `main()`을 실행합니다.

### Run Test Codes

```shell
# pytest로 테스트 실행
$ uv run pytest

# 또는 등록된 스크립트로 실행
$ uv run test
```