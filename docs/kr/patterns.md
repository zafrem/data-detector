# 패턴 구조

## 패턴 파일 형식

패턴은 다음 구조를 가진 YAML 파일로 정의됩니다:

```yaml
namespace: kr
description: Korean (South Korea) PII patterns

patterns:
  - id: mobile_01              # 필수: 2자리 접미사가 있는 패턴 ID
    location: kr               # 필수: 위치 식별자 (kr, us, comm 등)
    category: phone            # 필수: PII 카테고리
    description: Korean mobile phone number (010/011/016/017/018/019)
    pattern: '01[016-9]-?\d{3,4}-?\d{4}'  # 필수: 정규식 패턴
    flags: [IGNORECASE]        # 선택: 정규식 플래그
    mask: "***-****-****"      # 선택: 기본 마스크 템플릿
    verification: iban_mod97   # 선택: 검증 함수 이름
    examples:                  # 선택이지만 권장됨
      match: ["010-1234-5678", "01012345678"]
      nomatch: ["012-999-9999"]
    policy:                    # 선택: 개인정보 및 동작 정책
      store_raw: false
      action_on_match: redact
      severity: high
    metadata:                  # 선택: 추가 메타데이터
      note: "Additional information"
```

## 필수 필드

- **`id`**: 2자리 접미사가 있는 고유 식별자 (예: `mobile_01`, `ssn_02`)
- **`location`**: 위치/지역 코드 (2-4자 소문자: `kr`, `us`, `comm`, `intl`)
- **`category`**: 다음 중 PII 카테고리: `phone`, `ssn`, `rrn`, `email`, `bank`, `passport`, `address`, `credit_card`, `ip`, `iban`, `name`, `other`
- **`pattern`**: 매칭을 위한 정규식 패턴

## 선택 필드

### Flags
적용할 정규식 플래그:
- `IGNORECASE` - 대소문자 구분 없는 매칭
- `MULTILINE` - `^`와 `$`가 줄 경계와 일치
- `DOTALL` - `.`가 개행과 일치
- `UNICODE` - 유니코드 매칭
- `VERBOSE` - 정규식에 주석 허용

### Mask
수정을 위한 기본 마스크 템플릿 (예: `"***-****-****"`)

### Verification
정규식 매칭 후 적용할 검증 함수 이름. 자세한 내용은 [검증 함수](verification.md)를 참조하세요.

내장 검증 함수:
- `iban_mod97` - IBAN Mod-97 체크섬
- `luhn` - Luhn 알고리즘 (신용카드 등)

### Examples
패턴 검증을 위한 테스트 케이스:
- `match` - 패턴과 일치해야 하는 예제
- `nomatch` - 일치하지 않아야 하는 예제

### Policy
개인정보 및 동작 설정:
- `store_raw` (boolean) - 원시 일치 텍스트를 저장할 수 있는지 여부
- `action_on_match` (string) - 동작: `redact`, `report`, `tokenize`, `ignore`
- `severity` (string) - 심각도 수준: `low`, `medium`, `high`, `critical`

### Metadata
임의의 추가 데이터를 키-값 쌍으로.

## 위치 코드

`location` 필드는 지리적 또는 범주적 범위를 식별합니다:

- **`co`** - 공통/국제 패턴
- **`kr`** - 대한민국
- **`us`** - 미국
- **`tw`** - 대만 (중화민국)
- **`jp`** - 일본
- **`cn`** - 중국 (중화인민공화국)
- **`in`** - 인도
- **`eu`** - 유럽 연합 (향후)
- **`intl`** - 국제 (다중 지역)

**참고**: 패턴 파일은 임의의 이름을 가질 수 있습니다. 시스템은 `location` 필드를 사용하여 패턴을 구성합니다.

## 패턴 명명 모범 사례

- **ID 형식**: `{name}_{NN}` 여기서 NN은 2자리 숫자 (예: `mobile_01`, `mobile_02`)
- **위치 코드**: 2-4자 소문자 사용 (예: `kr`, `us`, `comm`, `myorg`)
- **버전 관리**: 패턴 변형에 대해 숫자 접미사 증가 (예: `ssn_01`, `ssn_02`)
