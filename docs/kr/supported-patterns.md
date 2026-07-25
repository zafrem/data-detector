# 지원 패턴

## 개요

data-detector는 여러 국가 및 카테고리에 걸쳐 PII를 감지하기 위한 내장 패턴을 포함합니다.

**총 패턴 수**: 60+
**위치**: 7개 (공통, KR, US, TW, JP, CN, IN)

## 공통/국제 (location: co)

### 이메일 및 네트워크
- `email_01` - 이메일 주소 (RFC 5322 간소화)
- `ipv4_01` - IPv4 주소
- `ipv6_01` - IPv6 주소 (간소화)
- `url_01` - http/https 프로토콜을 가진 URL

### 신용카드
- `credit_card_visa_01` - Visa 신용카드
- `credit_card_mastercard_01` - MasterCard 신용카드
- `credit_card_amex_01` - American Express 신용카드
- `credit_card_discover_01` - Discover 신용카드
- `credit_card_jcb_01` - JCB 신용카드
- `credit_card_diners_01` - Diners Club 신용카드

### IBAN (Mod-97 검증 포함)
- `iban_01` - 일반 IBAN (모든 국가)
- `iban_ad_01` - 안도라
- `iban_al_01` - 알바니아
- `iban_at_01` - 오스트리아
- `iban_de_01` - 독일
- `iban_fr_01` - 프랑스
- `iban_gb_01` - 영국
- `iban_it_01` - 이탈리아
- `iban_nl_01` - 네덜란드
- `iban_es_01` - 스페인

## 대한민국 (location: kr)

### 전화번호
- `mobile_01` - 휴대전화 번호 (010/011/016-019)
- `landline_01` - 유선전화 번호 (02/031-055/061-064)

### 국가 신분증
- `rrn_01` - 주민등록번호
- `business_registration_01` - 사업자등록번호
- `corporate_registration_01` - 법인등록번호
- `passport_01` - 여권 번호
- `driver_license_01` - 운전면허증 번호

### 금융
- `bank_account_01` - 은행 계좌번호

### 이름
- `korean_name_01` - 한국 이름 (한글)

## 미국 (location: us)

### 국가 신분증
- `ssn_01` - 사회보장번호 (SSN)
- `ein_01` - 고용주 식별 번호
- `itin_01` - 개인 납세자 식별 번호

### 전화 및 위치
- `phone_01` - 전화번호 (지역 코드 포함)
- `zipcode_01` - ZIP 코드 (5자리 및 ZIP+4)

### 문서
- `passport_01` - 여권 번호
- `driver_license_ca_01` - 캘리포니아 운전면허증
- `medicare_01` - Medicare 수혜자 식별자

## 대만 (location: tw)

### 전화번호
- `mobile_01` - 휴대전화 번호
- `landline_01` - 유선전화 번호

### 신분증 및 문서
- `national_id_01` - 국민 신분증 (身分證字號)
- `passport_01` - 여권 번호
- `business_id_01` - 사업자 통일 번호 (統一編號)

### 이름
- `chinese_name_01` - 번체 중국어 이름

## 일본 (location: jp)

### 전화번호
- `mobile_01` - 휴대전화 번호
- `landline_01` - 유선전화 번호

### 신분증 및 문서
- `my_number_01` - My Number (개인 번호)
- `passport_01` - 여권 번호
- `driver_license_01` - 운전면허증 번호
- `zipcode_01` - 우편번호

### 금융
- `bank_account_01` - 은행 계좌번호

### 이름
- `japanese_name_hiragana_01` - 일본 이름 (히라가나)
- `japanese_name_katakana_01` - 일본 이름 (가타카나)
- `japanese_name_kanji_01` - 일본 이름 (한자)

## 중국 (location: cn)

### 전화번호
- `mobile_01` - 휴대전화 번호
- `landline_01` - 유선전화 번호

### 신분증 및 문서
- `national_id_01` - 국민 신분증 (18자리)
- `passport_01` - 여권 번호
- `social_credit_01` - 통일 사회 신용 코드

### 금융
- `bank_card_01` - 은행 카드 번호

### 이름
- `chinese_name_01` - 간체 중국어 이름

## 인도 (location: in)

### 전화번호
- `mobile_01` - 휴대전화 번호
- `landline_01` - 유선전화 번호

### 신분증 및 문서
- `aadhaar_01` - Aadhaar 번호
- `pan_01` - PAN (영구 계좌 번호)
- `passport_01` - 여권 번호
- `voter_id_01` - 유권자 ID (EPIC)
- `driving_license_01` - 운전면허증

### 위치 및 금융
- `pincode_01` - PIN 코드
- `ifsc_01` - IFSC 코드
- `gst_01` - GST 번호

### 이름
- `indian_name_01` - 인도 이름 (라틴 문자)

## 카테고리

패턴은 다음 카테고리로 구성됩니다:

- **phone** - 전화번호
- **ssn** - 사회보장번호
- **rrn** - 주민등록번호
- **email** - 이메일 주소
- **bank** - 은행 계좌번호
- **passport** - 여권 번호
- **address** - 물리적 주소
- **credit_card** - 신용카드 번호
- **ip** - IP 주소
- **iban** - 국제 은행 계좌 번호
- **name** - 개인 이름
- **other** - 기타 PII 유형

## 심각도 수준

- **low** - IP 주소, URL
- **medium** - 이메일 주소, 이름
- **high** - 전화번호, 국가 신분증, IBAN
- **critical** - 신용카드, SSN, RRN, 은행 계좌

## 패턴 사용

### 네임스페이스별 찾기
```python
# 한국 패턴만 검색
result = engine.find(text, namespaces=["kr"])

# 여러 네임스페이스 검색
result = engine.find(text, namespaces=["kr", "us", "co"])
```

### 특정 패턴으로 찾기
```python
# 특정 패턴에 대해 검증
result = engine.validate("010-1234-5678", "kr/mobile_01")
```

### 모든 패턴 찾기
```python
# 로드된 모든 패턴 검색
result = engine.find(text)
```

## 패턴 정확도

### 검증 포함
검증 함수가 있는 패턴 (예: IBAN, Luhn이 있는 신용카드)은 더 높은 정확도를 가집니다:
- **IBAN 패턴**: ~99% 정확도 (Mod-97 검증)
- **신용카드 패턴**: Luhn 검증 추가 가능

### 정규식만 사용
검증이 없는 패턴은 정규식 매칭에만 의존합니다:
- **전화번호**: 형식 검증만
- **신분증**: 형식 및 길이 검증

정확도를 향상시키려면 사용 사례에 맞는 사용자 정의 검증 함수를 추가하는 것을 고려하십시오.

## 새 패턴 추가

자신만의 패턴을 추가하는 방법은 [사용자 정의 패턴](custom-patterns.md)을 참조하십시오.
