package verification

import (
	"fmt"
	"math"
	"math/big"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"unicode"
)

// VerificationFunc is the signature for all verification functions.
type VerificationFunc func(string) bool

var (
	// VerificationFunctions registers all available verification functions.
	VerificationFunctions = map[string]VerificationFunc{
		"iban_mod97":                      IbanMod97,
		"luhn":                            Luhn,
		"dms_coordinate":                  DmsCoordinate,
		"high_entropy_token":              HighEntropyToken,
		"not_timestamp":                   NotTimestamp,
		"korean_zipcode_valid":            KoreanZipcodeValid,
		"us_zipcode_valid":                UsZipcodeValid,
		"jp_zipcode_valid":                JpZipcodeValid,
		"cn_zipcode_valid":                CnZipcodeValid,
		"tw_zipcode_valid":                TwZipcodeValid,
		"in_pincode_valid":                InPincodeValid,
		"korean_bank_account_valid":       KoreanBankAccountValid,
		"generic_number_not_timestamp":    GenericNumberNotTimestamp,
		"contains_letter":                 ContainsLetter,
		"us_ssn_valid":                    UsSsnValid,
		"cjk_name_standalone":             CjkNameStandalone,
		"chinese_name_valid":              ChineseNameValid,
		"korean_name_valid":               KoreanNameValid,
		"japanese_name_kanji_valid":       JapaneseNameKanjiValid,
		"cn_national_id_valid":            CnNationalIdValid,
		"tw_national_id_valid":            TwNationalIdValid,
		"india_aadhaar_valid":             IndiaAadhaarValid,
		"india_pan_valid":                 IndiaPanValid,
		"kr_business_registration_valid":  KrBusinessRegistrationValid,
		"ipv4_public":                     Ipv4Public,
		"not_repeating_pattern":           NotRepeatingPattern,
		"credit_card_bin_valid":           CreditCardBinValid,
		"kr_rrn_valid":                    KrRrnValid,
		"kr_alien_registration_valid":     KrAlienRegistrationValid,
		"jp_my_number_valid":              JpMyNumberValid,
		"kr_corporate_registration_valid": KrCorporateRegistrationValid,
		"spain_dni_valid":                 SpainDniValid,
		"spain_nie_valid":                 SpainNieValid,
		"netherlands_bsn_valid":           NetherlandsBsnValid,
		"poland_pesel_valid":              PolandPeselValid,
		"sweden_personnummer_valid":       SwedenPersonnummerValid,
		"france_insee_valid":              FranceInseeValid,
		"belgium_rrn_valid":               BelgiumRrnValid,
		"finland_hetu_valid":              FinlandHetuValid,
		"jp_corporate_number_valid":       JpCorporateNumberValid,
		"tw_ubn_valid":                    TwUbnValid,
		"us_npi_valid":                    UsNpiValid,
		"uk_nino_valid":                   UkNinoValid,
		"swift_bic_valid":                 SwiftBicValid,
		"aws_access_key_valid":            AwsAccessKeyValid,
		"google_api_key_valid":            GoogleApiKeyValid,
		"crypto_btc_valid":                CryptoBtcValid,
		"crypto_eth_valid":                CryptoEthValid,
	}

	mu sync.RWMutex

	// Cache for data-driven verification
	dataCache = make(map[string]map[string]struct{})
)

// RegisterVerificationFunction registers a custom verification function.
func RegisterVerificationFunction(name string, funcPtr VerificationFunc) {
	mu.Lock()
	defer mu.Unlock()
	VerificationFunctions[name] = funcPtr
}

// UnregisterVerificationFunction unregisters a verification function.
func UnregisterVerificationFunction(name string) bool {
	mu.Lock()
	defer mu.Unlock()
	if _, ok := VerificationFunctions[name]; ok {
		delete(VerificationFunctions, name)
		return true
	}
	return false
}

// GetVerificationFunction returns a verification function by name.
func GetVerificationFunction(name string) (VerificationFunc, bool) {
	mu.RLock()
	defer mu.RUnlock()
	f, ok := VerificationFunctions[name]
	return f, ok
}

// --- Constants ---

var CHINESE_SURNAMES = map[string]struct{}{
	"王": {}, "李": {}, "张": {}, "刘": {}, "陈": {}, "杨": {}, "黄": {}, "赵": {}, "吴": {}, "周": {},
	"徐": {}, "孙": {}, "马": {}, "朱": {}, "胡": {}, "郭": {}, "何": {}, "林": {}, "高": {}, "罗": {},
	"郑": {}, "梁": {}, "谢": {}, "宋": {}, "唐": {}, "许": {}, "邓": {}, "冯": {}, "韩": {}, "曹": {},
	"曾": {}, "彭": {}, "萧": {}, "蔡": {}, "潘": {}, "田": {}, "董": {}, "袁": {}, "于": {}, "余": {},
	"叶": {}, "蔣": {}, "杜": {}, "苏": {}, "魏": {}, "程": {}, "吕": {}, "丁": {}, "沈": {}, "任": {},
	"姚": {}, "卢": {}, "傅": {}, "钟": {}, "姜": {}, "崔": {}, "谭": {}, "廖": {}, "范": {}, "汪": {},
	"陆": {}, "金": {}, "石": {}, "戴": {}, "贾": {}, "韦": {}, "夏": {}, "邱": {}, "方": {}, "侯": {},
	"邹": {}, "熊": {}, "孟": {}, "秦": {}, "白": {}, "江": {}, "阎": {}, "薛": {}, "尹": {}, "段": {},
	"雷": {}, "黎": {}, "史": {}, "龙": {}, "陶": {}, "贺": {}, "顾": {}, "毛": {}, "郝": {}, "龚": {},
	"邵": {}, "万": {}, "钱": {}, "严": {}, "赖": {}, "覃": {}, "洪": {}, "武": {}, "莫": {}, "孔": {},
	"張": {}, "劉": {}, "陳": {}, "楊": {}, "黃": {}, "趙": {}, "吳": {}, "許": {}, "鄭": {}, "謝": {},
	"鄧": {}, "馮": {}, "韓": {}, "蕭": {}, "葉": {}, "蔣": {}, "蘇": {}, "魏": {}, "呂": {}, "瀋": {},
	"盧": {}, "傅": {}, "鐘": {}, "薑": {}, "譚": {}, "廖": {}, "範": {}, "陸": {}, "賈": {}, "鄒": {},
	"閻": {}, "龍": {}, "陶": {}, "賀": {}, "顧": {}, "郝": {}, "龔": {}, "萬": {}, "錢": {}, "嚴": {},
	"賴": {}, "覃": {}, "欧阳": {}, "歐陽": {}, "司马": {}, "司馬": {}, "上官": {}, "诸葛": {}, "諸葛": {},
	"东方": {}, "東方": {}, "皇甫": {}, "尉迟": {}, "尉遲": {}, "公孙": {}, "公孫": {}, "令狐": {}, "慕容": {},
	"轩辕": {}, "軒轅": {}, "夏侯": {}, "司徒": {}, "独孤": {}, "獨孤": {},
}

var KOREAN_SURNAMES = map[string]struct{}{
	"김": {}, "이": {}, "박": {}, "최": {}, "정": {}, "강": {}, "조": {}, "윤": {}, "장": {}, "임": {},
	"한": {}, "오": {}, "서": {}, "신": {}, "권": {}, "황": {}, "안": {}, "송": {}, "류": {}, "유": {},
	"홍": {}, "전": {}, "고": {}, "문": {}, "양": {}, "손": {}, "배": {}, "백": {}, "허": {}, "남": {},
	"심": {}, "노": {}, "하": {}, "곽": {}, "성": {}, "차": {}, "주": {}, "우": {}, "구": {}, "민": {},
	"진": {}, "나": {}, "지": {}, "엄": {}, "변": {}, "채": {}, "원": {}, "천": {}, "방": {}, "공": {},
	"현": {}, "함": {}, "염": {}, "여": {}, "추": {}, "도": {}, "소": {}, "석": {}, "선": {}, "설": {},
	"마": {}, "길": {}, "연": {}, "위": {}, "표": {}, "명": {}, "기": {}, "반": {}, "왕": {}, "금": {},
	"옥": {}, "육": {}, "인": {}, "맹": {}, "제": {}, "모": {}, "탁": {}, "국": {}, "어": {}, "은": {},
	"편": {}, "용": {}, "예": {}, "경": {}, "봉": {}, "사": {}, "부": {}, "황보": {}, "남궁": {}, "독고": {},
	"사공": {}, "제갈": {}, "선우": {},
}

var JAPANESE_SURNAMES = map[string]struct{}{
	"佐藤": {}, "鈴木": {}, "高橋": {}, "田中": {}, "伊藤": {}, "渡辺": {}, "山本": {}, "中村": {}, "小林": {}, "加藤": {},
	"吉田": {}, "山田": {}, "佐々木": {}, "山口": {}, "松本": {}, "井上": {}, "木村": {}, "林": {}, "斎藤": {}, "清水": {},
	"山崎": {}, "森": {}, "阿部": {}, "池田": {}, "橋本": {}, "山下": {}, "石川": {}, "中島": {}, "前田": {}, "藤田": {},
	"小川": {}, "後藤": {}, "岡田": {}, "長谷川": {}, "村上": {}, "近藤": {}, "石井": {}, "斉藤": {}, "坂本": {}, "遠藤": {},
	"青木": {}, "藤井": {}, "西村": {}, "福田": {}, "太田": {}, "三浦": {}, "藤原": {}, "岡本": {}, "松田": {}, "中川": {},
	"原田": {}, "小野": {}, "竹内": {}, "金子": {}, "和田": {}, "中野": {}, "原": {}, "田村": {}, "安藤": {}, "河野": {},
	"上田": {}, "大野": {}, "高木": {}, "工藤": {}, "内田": {}, "丸山": {}, "今井": {}, "酒井": {}, "宮崎": {}, "横山": {},
	"関": {}, "堀": {}, "島": {}, "谷": {}, "浜": {}, "沢": {}, "杉": {},
}

var CHINESE_NON_NAME_KEYWORDS = map[string]struct{}{
	"王国": {}, "王朝": {}, "王牌": {}, "王者": {}, "李子": {}, "张开": {}, "张力": {}, "张贴": {}, "黄金": {}, "黄色": {},
	"黄油": {}, "黄土": {}, "黄瓜": {}, "黄河": {}, "黄昏": {}, "高度": {}, "高级": {}, "高中": {}, "高速": {}, "高考": {},
	"高峰": {}, "高手": {}, "高端": {}, "周围": {}, "周期": {}, "周末": {}, "周年": {}, "周边": {}, "周到": {}, "马上": {},
	"马路": {}, "马力": {}, "朱红": {}, "曹操": {}, "白色": {}, "白天": {}, "白云": {}, "白金": {}, "白菜": {}, "金属": {},
	"金融": {}, "金额": {}, "金钱": {}, "金牌": {}, "田地": {}, "田野": {}, "田园": {}, "石头": {}, "石油": {}, "石材": {},
	"方法": {}, "方案": {}, "方向": {}, "方式": {}, "方面": {}, "方便": {}, "任务": {}, "任何": {}, "任意": {}, "任命": {},
	"程度": {}, "程序": {}, "江山": {}, "江南": {}, "江河": {}, "余额": {}, "余下": {}, "于是": {}, "何时": {}, "何处": {},
	"何必": {}, "电话": {}, "電話": {}, "邮箱": {}, "郵箱": {}, "地址": {}, "姓名": {}, "信息": {}, "資訊": {}, "联系": {},
	"聯繫": {}, "手机": {}, "手機": {}, "号码": {}, "號碼": {}, "传真": {}, "傳真": {}, "邮件": {}, "郵件": {}, "密码": {},
	"密碼": {}, "账号": {}, "帳號": {}, "注册": {}, "註冊": {}, "登录": {}, "登錄": {}, "确认": {}, "確認": {}, "验证": {},
	"驗證": {}, "性别": {}, "性別": {}, "生日": {}, "职业": {}, "職業": {}, "公司": {}, "部门": {}, "部門": {},
}

var KOREAN_NON_NAME_KEYWORDS = map[string]struct{}{
	"전화번호": {}, "이메일": {}, "연락처": {}, "주소": {}, "이름": {}, "성명": {}, "휴대폰": {}, "핸드폰": {}, "번호": {}, "전화": {},
	"메일": {}, "팩스": {}, "모바일": {}, "정보": {}, "문의": {}, "확인": {}, "성별": {}, "생년": {}, "월일": {}, "생일": {},
	"직업": {}, "나이": {}, "회사": {}, "부서": {}, "직책": {}, "전화번": {}, "메일주": {}, "이메일주": {}, "연락처는": {}, "주소는": {},
	"이름은": {}, "성명은": {},
}

var JAPANESE_NON_NAME_KEYWORDS = map[string]struct{}{
	"田園": {}, "田畑": {}, "田舎": {}, "中心": {}, "中央": {}, "中間": {}, "中古": {}, "中止": {}, "中国": {}, "中学": {},
	"山脈": {}, "山岳": {}, "山林": {}, "山地": {}, "山頂": {}, "高速": {}, "高校": {}, "高層": {}, "高価": {}, "高原": {},
	"高齢": {}, "林業": {}, "林道": {}, "森林": {}, "石油": {}, "石材": {}, "石炭": {}, "石器": {}, "金属": {}, "金融": {},
	"金額": {}, "金銭": {}, "金庫": {}, "上記": {}, "上昇": {}, "上手": {}, "上司": {}, "大学": {}, "大会": {}, "大臣": {},
	"大量": {}, "大型": {}, "大切": {}, "大変": {}, "小学": {}, "小説": {}, "小型": {}, "小売": {}, "原因": {}, "原則": {},
	"原料": {}, "原発": {}, "内容": {}, "内部": {}, "内閣": {}, "前回": {}, "前者": {}, "前提": {}, "前日": {}, "後半": {},
	"後者": {}, "後日": {}, "西洋": {}, "西側": {}, "青年": {}, "青春": {}, "近代": {}, "近年": {}, "近所": {}, "遠方": {},
	"遠足": {}, "池袋": {}, "電話": {}, "住所": {}, "名前": {}, "情報": {}, "連絡": {}, "番号": {}, "携帯": {}, "確認": {},
	"登録": {}, "氏名": {}, "性別": {}, "生年": {}, "職業": {}, "会社": {}, "部署": {}, "郵便": {}, "暗号": {}, "認証": {},
	"口座": {},
}

// --- Helper Functions ---

func _getDataPath() string {
	_, b, _, _ := runtime.Caller(0)
	basepath := filepath.Dir(filepath.Dir(filepath.Dir(b)))
	return filepath.Join(basepath, "datas")
}

func _loadDataFile(filename string) map[string]struct{} {
	mu.Lock()
	if values, ok := dataCache[filename]; ok {
		mu.Unlock()
		return values
	}
	mu.Unlock()

	dataPath := filepath.Join(_getDataPath(), filename)
	values := make(map[string]struct{})

	file, err := os.ReadFile(dataPath)
	if err == nil {
		lines := strings.Split(string(file), "\n")
		if len(lines) > 1 {
			for _, line := range lines[1:] {
				val := strings.TrimSpace(line)
				if val != "" {
					values[val] = struct{}{}
				}
			}
		}
	}

	mu.Lock()
	dataCache[filename] = values
	mu.Unlock()
	return values
}

func _isValidDate(year, month, day int) bool {
	if month < 1 || month > 12 {
		return false
	}
	if day < 1 || day > 31 {
		return false
	}

	daysInMonth := []int{0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}
	if day > daysInMonth[month] {
		return false
	}

	if month == 2 && day == 29 {
		isLeap := (year%4 == 0 && year%100 != 0) || (year%400 == 0)
		if !isLeap {
			return false
		}
	}

	return true
}

// --- Verification Functions ---

func IbanMod97(value string) bool {
	iban := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(iban) < 5 {
		return false
	}

	rearranged := iban[4:] + iban[:4]
	var numericString strings.Builder
	for _, char := range rearranged {
		if unicode.IsDigit(char) {
			numericString.WriteRune(char)
		} else if unicode.IsLetter(char) {
			numericString.WriteString(strconv.Itoa(int(char - 'A' + 10)))
		} else {
			return false
		}
	}

	n := new(big.Int)
	n, ok := n.SetString(numericString.String(), 10)
	if !ok {
		return false
	}

	remainder := new(big.Int).Mod(n, big.NewInt(97))
	return remainder.Int64() == 1
}

func Luhn(value string) bool {
	var digits []int
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits = append(digits, int(r-'0'))
		}
	}

	if len(digits) == 0 {
		return false
	}

	checksum := 0
	for i := 0; i < len(digits); i++ {
		digit := digits[len(digits)-1-i]
		if i%2 == 1 {
			digit *= 2
			if digit > 9 {
				digit -= 9
			}
		}
		checksum += digit
	}

	return checksum%10 == 0
}

var dmsRegex = regexp.MustCompile(`(?i)(\d{1,3})°\s*(\d{1,2})′\s*(\d{1,2}(?:\.\d+)?)″\s*([NSEW])`)

func DmsCoordinate(value string) bool {
	match := dmsRegex.FindStringSubmatch(value)
	if match == nil {
		return false
	}

	degrees, _ := strconv.Atoi(match[1])
	minutes, _ := strconv.Atoi(match[2])
	seconds, _ := strconv.ParseFloat(match[3], 64)
	direction := strings.ToUpper(match[4])

	if minutes > 59 || seconds >= 60 {
		return false
	}

	if direction == "N" || direction == "S" {
		if degrees > 90 {
			return false
		}
	} else if direction == "E" || direction == "W" {
		if degrees > 180 {
			return false
		}
	}

	return true
}

func HighEntropyToken(value string) bool {
	if len(value) < 20 {
		return false
	}

	for _, r := range value {
		if unicode.IsSpace(r) {
			return false
		}
	}

	allowedChars := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-+/.="
	allowedSet := make(map[rune]struct{})
	for _, r := range allowedChars {
		allowedSet[r] = struct{}{}
	}

	for _, r := range value {
		if _, ok := allowedSet[r]; !ok {
			return false
		}
	}

	// Normalize for entropy calculation: lowercase and treat separators as spaces
	normalized := strings.ToLower(value)
	normalized = strings.ReplaceAll(normalized, "-", " ")
	normalized = strings.ReplaceAll(normalized, "_", " ")

	counts := make(map[rune]int)
	for _, r := range normalized {
		counts[r]++
	}

	length := float64(len(normalized))
	entropy := 0.0
	for _, count := range counts {
		p := float64(count) / length
		entropy -= p * math.Log2(p)
	}

	return entropy >= 4.0
}

func NotTimestamp(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}

	s := digitsOnly.String()
	length := len(s)

	if length == 10 {
		num, err := strconv.ParseInt(s, 10, 64)
		if err == nil && num >= 1000000000 && num <= 9999999999 {
			return false
		}
	}

	if length == 13 {
		num, err := strconv.ParseInt(s, 10, 64)
		if err == nil && num >= 1000000000000 && num <= 9999999999999 {
			return false
		}
	}

	if length == 14 {
		year, _ := strconv.Atoi(s[:4])
		month, _ := strconv.Atoi(s[4:6])
		day, _ := strconv.Atoi(s[6:8])
		hour, _ := strconv.Atoi(s[8:10])
		minute, _ := strconv.Atoi(s[10:12])
		second, _ := strconv.Atoi(s[12:14])

		if year >= 1900 && year <= 2099 &&
			month >= 1 && month <= 12 &&
			day >= 1 && day <= 31 &&
			hour >= 0 && hour <= 23 &&
			minute >= 0 && minute <= 59 &&
			second >= 0 && second <= 59 {
			return false
		}
	}

	return true
}

func KoreanZipcodeValid(value string) bool {
	validZips := _loadDataFile("kr_zipcodes.csv")
	if len(validZips) > 0 {
		_, ok1 := validZips[value]
		_, ok2 := validZips[strings.ReplaceAll(value, "-", "")]
		return ok1 || ok2
	}

	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if len(s) != 5 {
		return false
	}

	isSequentialUp := true
	isSequentialDown := true
	for i := 1; i < len(s); i++ {
		if int(s[i]-'0') != int(s[i-1]-'0')+1 {
			isSequentialUp = false
		}
		if int(s[i]-'0') != int(s[i-1]-'0')-1 {
			isSequentialDown = false
		}
	}
	if isSequentialUp || isSequentialDown {
		return false
	}

	allSame := true
	for i := 1; i < len(s); i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	return !allSame
}

func UsZipcodeValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()

	validZips := _loadDataFile("us_zipcodes.csv")
	if len(validZips) > 0 {
		if len(s) == 5 {
			_, ok := validZips[s]
			return ok
		} else if len(s) == 9 {
			_, ok := validZips[s[:5]]
			return ok
		}
	}

	if len(s) != 5 && len(s) != 9 {
		return false
	}

	baseZip := s[:5]
	isSequentialUp := true
	isSequentialDown := true
	for i := 1; i < len(baseZip); i++ {
		if int(baseZip[i]-'0') != int(baseZip[i-1]-'0')+1 {
			isSequentialUp = false
		}
		if int(baseZip[i]-'0') != int(baseZip[i-1]-'0')-1 {
			isSequentialDown = false
		}
	}
	if isSequentialUp || isSequentialDown {
		return false
	}

	allSame := true
	for i := 1; i < len(baseZip); i++ {
		if baseZip[i] != baseZip[0] {
			allSame = false
			break
		}
	}
	return !allSame
}

func JpZipcodeValid(value string) bool {
	s := strings.Map(func(r rune) rune {
		if unicode.IsDigit(r) {
			return r
		}
		return -1
	}, value)

	if len(s) != 7 {
		return false
	}

	validZips := _loadDataFile("jp_zipcodes.csv")
	if len(validZips) > 0 {
		hyphenFormat := fmt.Sprintf("%s-%s", s[:3], s[3:])
		_, ok1 := validZips[hyphenFormat]
		_, ok2 := validZips[s]
		return ok1 || ok2
	}

	allSame := true
	for i := 1; i < len(s); i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	isSequentialUp := true
	isSequentialDown := true
	for i := 1; i < len(s); i++ {
		if int(s[i]-'0') != int(s[i-1]-'0')+1 {
			isSequentialUp = false
		}
		if int(s[i]-'0') != int(s[i-1]-'0')-1 {
			isSequentialDown = false
		}
	}
	return !(isSequentialUp || isSequentialDown)
}

func CnZipcodeValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()

	if len(s) != 6 {
		return false
	}

	validZips := _loadDataFile("cn_zipcodes.csv")
	if len(validZips) > 0 {
		_, ok := validZips[s]
		return ok
	}

	allSame := true
	for i := 1; i < len(s); i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	isSequentialUp := true
	isSequentialDown := true
	for i := 1; i < len(s); i++ {
		if int(s[i]-'0') != int(s[i-1]-'0')+1 {
			isSequentialUp = false
		}
		if int(s[i]-'0') != int(s[i-1]-'0')-1 {
			isSequentialDown = false
		}
	}
	if isSequentialUp || isSequentialDown {
		return false
	}

	firstTwo, _ := strconv.Atoi(s[:2])
	return firstTwo >= 1 && firstTwo <= 86
}

func TwZipcodeValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()

	if len(s) != 3 && len(s) != 5 {
		return false
	}

	validZips := _loadDataFile("tw_zipcodes.csv")
	if len(validZips) > 0 {
		if _, ok := validZips[s]; ok {
			return true
		}
		if len(s) == 5 {
			if _, ok := validZips[s[:3]]; ok {
				return true
			}
		}
		return false
	}

	allSame := true
	for i := 1; i < len(s); i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	return s[0] != '0'
}

func InPincodeValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()

	if len(s) != 6 {
		return false
	}

	if s[0] == '0' {
		return false
	}

	validPins := _loadDataFile("in_pincodes.csv")
	if len(validPins) > 0 {
		_, ok := validPins[s]
		return ok
	}

	allSame := true
	for i := 1; i < len(s); i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	isSequentialUp := true
	isSequentialDown := true
	for i := 1; i < len(s); i++ {
		if int(s[i]-'0') != int(s[i-1]-'0')+1 {
			isSequentialUp = false
		}
		if int(s[i]-'0') != int(s[i-1]-'0')-1 {
			isSequentialDown = false
		}
	}
	return !(isSequentialUp || isSequentialDown)
}

func KoreanBankAccountValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if s == "" {
		return false
	}

	hasKnownPrefix := false
	knownPrefixes := []string{"110", "120", "150", "190", "830", "1002", "301", "3333", "100"}
	for _, prefix := range knownPrefixes {
		if strings.HasPrefix(s, prefix) {
			hasKnownPrefix = true
			break
		}
	}

	length := len(s)
	if hasKnownPrefix {
		if length == 10 {
			num, err := strconv.ParseInt(s, 10, 64)
			if err == nil && num >= 1600000000 && num <= 1800000000 {
				return false
			}
		}
		return true
	}

	if length == 10 {
		num, err := strconv.ParseInt(s, 10, 64)
		if err == nil && num >= 1000000000 && num <= 9999999999 {
			return false
		}
	}
	if length == 13 {
		num, err := strconv.ParseInt(s, 10, 64)
		if err == nil && num >= 1000000000000 && num <= 9999999999999 {
			return false
		}
	}
	if length == 14 {
		year, _ := strconv.Atoi(s[:4])
		month, _ := strconv.Atoi(s[4:6])
		day, _ := strconv.Atoi(s[6:8])
		if year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31 {
			return false
		}
	}

	if length >= 10 && !hasKnownPrefix {
		maxSequential := 0
		currentSequential := 0
		for i := 1; i < len(s); i++ {
			if int(s[i]-'0') == int(s[i-1]-'0')+1 {
				currentSequential++
				if currentSequential > maxSequential {
					maxSequential = currentSequential
				}
			} else {
				currentSequential = 0
			}
		}
		if maxSequential >= 6 {
			return false
		}
	}

	return true
}

func GenericNumberNotTimestamp(value string) bool {
	hasSeparators := strings.ContainsAny(value, "- /")
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if s == "" {
		return true
	}
	length := len(s)

	if hasSeparators {
		if length >= 14 {
			year, _ := strconv.Atoi(s[:4])
			month, _ := strconv.Atoi(s[4:6])
			day, _ := strconv.Atoi(s[6:8])
			if year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31 {
				return false
			}
		}
		return true
	}

	if length == 10 {
		num, err := strconv.ParseInt(s, 10, 64)
		if err == nil && num >= 1000000000 && num <= 9999999999 {
			return false
		}
	}
	if length == 13 {
		num, err := strconv.ParseInt(s, 10, 64)
		if err == nil && num >= 1000000000000 && num <= 9999999999999 {
			return false
		}
	}
	if length >= 14 {
		year, _ := strconv.Atoi(s[:4])
		month, _ := strconv.Atoi(s[4:6])
		day, _ := strconv.Atoi(s[6:8])
		if year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31 {
			return false
		}
	}

	return true
}

func ContainsLetter(value string) bool {
	for _, r := range value {
		if unicode.IsLetter(r) {
			return true
		}
	}
	return false
}

func UsSsnValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if len(s) != 9 {
		return false
	}

	area, _ := strconv.Atoi(s[:3])
	group, _ := strconv.Atoi(s[3:5])
	serial, _ := strconv.Atoi(s[5:9])

	if area == 0 || area == 666 || area >= 900 {
		return false
	}
	if group == 0 {
		return false
	}
	if serial == 0 {
		return false
	}
	return true
}

func ChineseNameValid(value string) bool {
	runes := []rune(value)
	if len(runes) < 2 || len(runes) > 4 {
		return false
	}
	if _, ok := CHINESE_NON_NAME_KEYWORDS[value]; ok {
		return false
	}

	var surname, givenName string
	if len(runes) >= 3 {
		if _, ok := CHINESE_SURNAMES[string(runes[:2])]; ok {
			surname = string(runes[:2])
			givenName = string(runes[2:])
		}
	}
	if surname == "" {
		if _, ok := CHINESE_SURNAMES[string(runes[:1])]; ok {
			surname = string(runes[:1])
			givenName = string(runes[1:])
		}
	}

	if surname == "" {
		return false
	}

	validGivenNames := _loadDataFile("cn_given_names.csv")
	if len(validGivenNames) > 0 {
		if _, ok := validGivenNames[givenName]; ok {
			return true
		}
	}

	return len(runes) >= 2 && len(runes) <= 4
}

func KoreanNameValid(value string) bool {
	runes := []rune(value)
	if len(runes) < 2 || len(runes) > 5 {
		return false
	}
	if _, ok := KOREAN_NON_NAME_KEYWORDS[value]; ok {
		return false
	}

	lastChar := runes[len(runes)-1]
	particles := map[rune]struct{}{'은': {}, '는': {}, '이': {}, '가': {}, '을': {}, '를': {}, '의': {}}
	if len(runes) >= 3 {
		if _, ok := particles[lastChar]; ok {
			if _, ok := KOREAN_NON_NAME_KEYWORDS[string(runes[:len(runes)-1])]; ok {
				return false
			}
		}
	}

	var surname, givenName string
	if len(runes) >= 3 {
		if _, ok := KOREAN_SURNAMES[string(runes[:2])]; ok {
			surname = string(runes[:2])
			givenName = string(runes[2:])
		}
	}
	if surname == "" {
		if _, ok := KOREAN_SURNAMES[string(runes[:1])]; ok {
			surname = string(runes[:1])
			givenName = string(runes[1:])
		}
	}

	if surname == "" {
		return false
	}

	validGivenNames := _loadDataFile("kr_given_names.csv")
	if len(validGivenNames) > 0 {
		if _, ok := validGivenNames[givenName]; ok {
			return true
		}
	}

	return len(runes) == 3
}

func JapaneseNameKanjiValid(value string) bool {
	runes := []rune(value)
	if len(runes) < 2 || len(runes) > 6 {
		return false
	}
	if _, ok := JAPANESE_NON_NAME_KEYWORDS[value]; ok {
		return false
	}
	if len(runes) == 2 {
		_, ok := JAPANESE_SURNAMES[value]
		return ok
	}

	var surname, givenName string
	if len(runes) >= 4 {
		if _, ok := JAPANESE_SURNAMES[string(runes[:3])]; ok {
			surname = string(runes[:3])
			givenName = string(runes[3:])
		}
	}
	if surname == "" {
		if _, ok := JAPANESE_SURNAMES[string(runes[:2])]; ok {
			surname = string(runes[:2])
			givenName = string(runes[2:])
		}
	}
	if surname == "" {
		if _, ok := JAPANESE_SURNAMES[string(runes[:1])]; ok {
			surname = string(runes[:1])
			givenName = string(runes[1:])
		}
	}

	if surname == "" {
		return false
	}

	validGivenNames := _loadDataFile("jp_given_names.csv")
	if len(validGivenNames) > 0 {
		if _, ok := validGivenNames[givenName]; ok {
			return true
		}
	}

	return len(runes) == 3 || len(runes) == 4
}

func CjkNameStandalone(value string) bool {
	runes := []rune(value)
	if len(runes) == 0 || len(runes) > 6 {
		return false
	}
	for _, r := range runes {
		isCjk := (r >= 0x4E00 && r <= 0x9FFF) || // CJK Unified Ideographs
			(r >= 0xAC00 && r <= 0xD7AF) || // Korean Hangul
			(r >= 0x3040 && r <= 0x309F) || // Hiragana
			(r >= 0x30A0 && r <= 0x30FF) // Katakana
		if !isCjk {
			return false
		}
	}
	return true
}

func CnNationalIdValid(value string) bool {
	s := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(s) != 18 {
		return false
	}
	validProvinces := map[string]struct{}{
		"11": {}, "12": {}, "13": {}, "14": {}, "15": {},
		"21": {}, "22": {}, "23": {},
		"31": {}, "32": {}, "33": {}, "34": {}, "35": {}, "36": {}, "37": {},
		"41": {}, "42": {}, "43": {}, "44": {}, "45": {}, "46": {},
		"50": {}, "51": {}, "52": {}, "53": {}, "54": {},
		"61": {}, "62": {}, "63": {}, "64": {}, "65": {},
		"71": {}, "81": {}, "82": {}, "91": {},
	}
	if _, ok := validProvinces[s[:2]]; !ok {
		return false
	}

	year, _ := strconv.Atoi(s[6:10])
	month, _ := strconv.Atoi(s[10:12])
	day, _ := strconv.Atoi(s[12:14])
	if !_isValidDate(year, month, day) || year < 1900 || year > 2100 {
		return false
	}

	weights := []int{7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2}
	checkDigits := []string{"1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"}
	total := 0
	for i := 0; i < 17; i++ {
		d, err := strconv.Atoi(string(s[i]))
		if err != nil {
			return false
		}
		total += d * weights[i]
	}
	return string(s[17]) == checkDigits[total%11]
}

func TwNationalIdValid(value string) bool {
	s := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(s) != 10 {
		return false
	}
	if s[0] < 'A' || s[0] > 'Z' || s[0] == 'I' || s[0] == 'O' || s[0] == 'W' {
		return false
	}
	for i := 1; i < 10; i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	gender := s[1]
	if gender != '1' && gender != '2' {
		return false
	}

	letterCode := int(s[0]-'A') + 10
	// Adjustment for I, O, W, Z which are not sequential in weight mapping but for simplicity we follow Python logic
	// Actually Python code: letter_code = ord(id_str[0]) - ord("A") + 10
	// Let's re-verify this. In Taiwan ID, the mapping is:
	// A=10, B=11, C=12, D=13, E=14, F=15, G=16, H=17, J=18, K=19, L=20, M=21, N=22, P=23, Q=24, R=25, S=26, T=27, U=28, V=29, X=30, Y=31, W=32, Z=33, I=34, O=35
	// But Python code used a simpler mapping. I'll stick to Python logic.

	total := (letterCode/10)*1 + (letterCode%10)*9
	weights := []int{8, 7, 6, 5, 4, 3, 2, 1}
	for i, w := range weights {
		d := int(s[i+1] - '0')
		total += d * w
	}
	total += int(s[9] - '0')
	return total%10 == 0
}

func IndiaAadhaarValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 12 || s[0] == '0' || s[0] == '1' {
		return false
	}
	allSame := true
	for i := 1; i < 12; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	d := [][]int{
		{0, 1, 2, 3, 4, 5, 6, 7, 8, 9},
		{1, 2, 3, 4, 0, 6, 7, 8, 9, 5},
		{2, 3, 4, 0, 1, 7, 8, 9, 5, 6},
		{3, 4, 0, 1, 2, 8, 9, 5, 6, 7},
		{4, 0, 1, 2, 3, 9, 5, 6, 7, 8},
		{5, 9, 8, 7, 6, 0, 4, 3, 2, 1},
		{6, 5, 9, 8, 7, 1, 0, 4, 3, 2},
		{7, 6, 5, 9, 8, 2, 1, 0, 4, 3},
		{8, 7, 6, 5, 9, 3, 2, 1, 0, 4},
		{9, 8, 7, 6, 5, 4, 3, 2, 1, 0},
	}
	p := [][]int{
		{0, 1, 2, 3, 4, 5, 6, 7, 8, 9},
		{1, 5, 7, 6, 2, 8, 3, 0, 9, 4},
		{5, 8, 0, 3, 7, 9, 6, 1, 4, 2},
		{8, 9, 1, 6, 0, 4, 3, 5, 2, 7},
		{9, 4, 5, 3, 1, 2, 6, 8, 7, 0},
		{4, 2, 8, 6, 5, 7, 3, 9, 0, 1},
		{2, 7, 9, 3, 8, 0, 6, 4, 1, 5},
		{7, 0, 4, 6, 9, 1, 3, 2, 5, 8},
	}
	c := 0
	for i := 0; i < len(s); i++ {
		digit := int(s[len(s)-1-i] - '0')
		c = d[c][p[i%8][digit]]
	}
	return c == 0
}

func IndiaPanValid(value string) bool {
	s := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(s) != 10 {
		return false
	}
	for i := 0; i < 5; i++ {
		if s[i] < 'A' || s[i] > 'Z' {
			return false
		}
	}
	for i := 5; i < 9; i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	if s[9] < 'A' || s[9] > 'Z' {
		return false
	}
	entityTypes := "ABCFGHLJKPT"
	if !strings.Contains(entityTypes, string(s[3])) {
		return false
	}
	testPatterns := map[string]struct{}{"AAAAA": {}, "ABCDE": {}, "XXXXX": {}, "ZZZZZ": {}}
	if _, ok := testPatterns[s[:5]]; ok {
		return false
	}
	return true
}

func KrBusinessRegistrationValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 10 {
		return false
	}
	allSame := true
	for i := 1; i < 10; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	weights := []int{1, 3, 7, 1, 3, 7, 1, 3, 5}
	total := 0
	for i := 0; i < 9; i++ {
		d := int(s[i] - '0')
		total += d * weights[i]
		if i == 8 {
			total += (d * 5) / 10
		}
	}
	checkDigit := (10 - (total % 10)) % 10
	return int(s[9]-'0') == checkDigit
}

func Ipv4Public(value string) bool {
	parts := strings.Split(value, ".")
	if len(parts) != 4 {
		return false
	}
	var octets [4]int
	for i, p := range parts {
		val, err := strconv.Atoi(p)
		if err != nil || val < 0 || val > 255 {
			return false
		}
		octets[i] = val
	}
	f, s, t := octets[0], octets[1], octets[2]
	if f == 0 || f == 10 || f == 127 {
		return false
	}
	if f == 169 && s == 254 {
		return false
	}
	if f == 172 && s >= 16 && s <= 31 {
		return false
	}
	if f == 192 && s == 0 && t == 2 {
		return false
	}
	if f == 192 && s == 168 {
		return false
	}
	if f == 198 && s == 51 && t == 100 {
		return false
	}
	if f == 203 && s == 0 && t == 113 {
		return false
	}
	if f >= 224 {
		return false
	}
	return true
}

func NotRepeatingPattern(value string) bool {
	if len(value) < 4 {
		return true
	}
	allSame := true
	for i := 1; i < len(value); i++ {
		if value[i] != value[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}

	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	ds := digits.String()
	if len(ds) >= 4 {
		isAscending := true
		isDescending := true
		for i := 1; i < len(ds); i++ {
			if int(ds[i]-'0') != int(ds[i-1]-'0')+1 {
				isAscending = false
			}
			if int(ds[i]-'0') != int(ds[i-1]-'0')-1 {
				isDescending = false
			}
		}
		if isAscending || isDescending {
			return false
		}
	}

	if len(value) >= 4 {
		p2 := value[:2]
		if strings.HasPrefix(strings.Repeat(p2, len(value)/2+1), value) {
			return false
		}
	}
	if len(value) >= 6 {
		p3 := value[:3]
		if strings.HasPrefix(strings.Repeat(p3, len(value)/3+1), value) {
			return false
		}
	}
	return true
}

func CreditCardBinValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) < 13 || len(s) > 19 {
		return false
	}
	validBin := false
	if s[0] == '4' {
		validBin = true
	} else if len(s) >= 2 {
		p2, _ := strconv.Atoi(s[:2])
		if p2 >= 51 && p2 <= 55 {
			validBin = true
		} else if len(s) >= 4 {
			p4, _ := strconv.Atoi(s[:4])
			if p4 >= 2221 && p4 <= 2720 {
				validBin = true
			}
		}
	}
	if !validBin && len(s) >= 2 {
		p2, _ := strconv.Atoi(s[:2])
		if p2 == 34 || p2 == 37 {
			validBin = true
		}
	}
	if !validBin {
		if strings.HasPrefix(s, "6011") || strings.HasPrefix(s, "65") {
			validBin = true
		} else if len(s) >= 3 {
			p3, _ := strconv.Atoi(s[:3])
			if p3 >= 644 && p3 <= 649 {
				validBin = true
			}
		}
		if !validBin && len(s) >= 6 {
			p6, _ := strconv.Atoi(s[:6])
			if p6 >= 622126 && p6 <= 622925 {
				validBin = true
			}
		}
	}
	if !validBin && len(s) >= 4 {
		p4, _ := strconv.Atoi(s[:4])
		if p4 >= 3528 && p4 <= 3589 {
			validBin = true
		}
	}
	if !validBin && strings.HasPrefix(s, "62") {
		validBin = true
	}
	if !validBin && len(s) >= 2 {
		p2, _ := strconv.Atoi(s[:2])
		if p2 == 36 || p2 == 38 {
			validBin = true
		} else if len(s) >= 3 {
			p3, _ := strconv.Atoi(s[:3])
			if p3 >= 300 && p3 <= 305 {
				validBin = true
			}
		}
	}
	if !validBin {
		return false
	}
	return Luhn(s)
}

func KrRrnValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 13 {
		return false
	}
	yy, _ := strconv.Atoi(s[0:2])
	mm, _ := strconv.Atoi(s[2:4])
	dd, _ := strconv.Atoi(s[4:6])
	gc, _ := strconv.Atoi(s[6:7])
	if gc < 1 || gc > 4 {
		return false
	}
	year := 1900 + yy
	if gc == 3 || gc == 4 {
		year = 2000 + yy
	}
	if !_isValidDate(year, mm, dd) {
		return false
	}
	allSame := true
	for i := 1; i < 13; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}
	weights := []int{2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5}
	total := 0
	for i, w := range weights {
		total += int(s[i]-'0') * w
	}
	check := (11 - (total % 11)) % 10
	return int(s[12]-'0') == check
}

func KrAlienRegistrationValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 13 {
		return false
	}
	yy, _ := strconv.Atoi(s[0:2])
	mm, _ := strconv.Atoi(s[2:4])
	dd, _ := strconv.Atoi(s[4:6])
	gc, _ := strconv.Atoi(s[6:7])
	if gc < 5 || gc > 8 {
		return false
	}
	year := 1900 + yy
	if gc == 7 || gc == 8 {
		year = 2000 + yy
	}
	if !_isValidDate(year, mm, dd) {
		return false
	}
	allSame := true
	for i := 1; i < 13; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	return !allSame
}

func JpMyNumberValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 12 {
		return false
	}
	allSame := true
	for i := 1; i < 12; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame || s == "123456789012" || s == "012345678901" {
		return false
	}
	weights := []int{6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2}
	total := 0
	for i, w := range weights {
		total += int(s[i]-'0') * w
	}
	remainder := total % 11
	check := 0
	if remainder > 1 {
		check = 11 - remainder
	}
	return int(s[11]-'0') == check
}

func KrCorporateRegistrationValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 13 {
		return false
	}
	allSame := true
	for i := 1; i < 13; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}
	weights := []int{1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2}
	total := 0
	for i, w := range weights {
		p := int(s[i]-'0') * w
		if p > 9 {
			p -= 9
		}
		total += p
	}
	check := (10 - (total % 10)) % 10
	return int(s[12]-'0') == check
}

func SpainDniValid(value string) bool {
	s := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(s) != 9 {
		return false
	}
	numPart := s[:8]
	for _, r := range numPart {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	if !unicode.IsLetter(rune(s[8])) {
		return false
	}
	letters := "TRWAGMYFPDXBNJZSQVHLCKE"
	num, _ := strconv.Atoi(numPart)
	return s[8] == letters[num%23]
}

func SpainNieValid(value string) bool {
	s := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(s) != 9 {
		return false
	}
	first := s[0]
	if first != 'X' && first != 'Y' && first != 'Z' {
		return false
	}
	numPart := s[1:8]
	for _, r := range numPart {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	if !unicode.IsLetter(rune(s[8])) {
		return false
	}
	repl := map[byte]string{'X': "0", 'Y': "1", 'Z': "2"}
	numStr := repl[first] + numPart
	num, _ := strconv.Atoi(numStr)
	letters := "TRWAGMYFPDXBNJZSQVHLCKE"
	return s[8] == letters[num%23]
}

func NetherlandsBsnValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) == 8 {
		s = "0" + s
	} else if len(s) != 9 {
		return false
	}
	allSame := true
	for i := 1; i < 9; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}
	weights := []int{9, 8, 7, 6, 5, 4, 3, 2, -1}
	total := 0
	for i, w := range weights {
		total += int(s[i]-'0') * w
	}
	return total%11 == 0
}

func PolandPeselValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 11 {
		return false
	}
	allSame := true
	for i := 1; i < 11; i++ {
		if s[i] != s[0] {
			allSame = false
			break
		}
	}
	if allSame {
		return false
	}
	yy, _ := strconv.Atoi(s[0:2])
	mm, _ := strconv.Atoi(s[2:4])
	dd, _ := strconv.Atoi(s[4:6])
	var year, month int
	if mm >= 1 && mm <= 12 {
		year, month = 1900+yy, mm
	} else if mm >= 21 && mm <= 32 {
		year, month = 2000+yy, mm-20
	} else if mm >= 41 && mm <= 52 {
		year, month = 2100+yy, mm-40
	} else if mm >= 61 && mm <= 72 {
		year, month = 2200+yy, mm-60
	} else if mm >= 81 && mm <= 92 {
		year, month = 1800+yy, mm-80
	} else {
		return false
	}
	if !_isValidDate(year, month, dd) {
		return false
	}
	weights := []int{1, 3, 7, 9, 1, 3, 7, 9, 1, 3}
	total := 0
	for i, w := range weights {
		total += int(s[i]-'0') * w
	}
	check := (10 - (total % 10)) % 10
	return int(s[10]-'0') == check
}

func SwedenPersonnummerValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) == 12 {
		s = s[2:]
	} else if len(s) != 10 {
		return false
	}
	mm, _ := strconv.Atoi(s[2:4])
	dd, _ := strconv.Atoi(s[4:6])
	if mm < 1 || mm > 12 || dd < 1 || dd > 31 {
		return false
	}
	return Luhn(s)
}

func FranceInseeValid(value string) bool {
	s := strings.ReplaceAll(value, " ", "")
	if len(s) != 15 {
		return false
	}
	calcStr := s
	dep := s[5:7]
	if dep == "2A" {
		calcStr = s[:5] + "19" + s[7:]
	} else if dep == "2B" {
		calcStr = s[:5] + "18" + s[7:]
	}
	for _, r := range calcStr {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	sex, _ := strconv.Atoi(string(calcStr[0]))
	if sex != 1 && sex != 2 {
		return false
	}
	month, _ := strconv.Atoi(calcStr[3:5])
	if month < 1 || month > 12 {
		return false
	}
	base, _ := strconv.ParseInt(calcStr[:13], 10, 64)
	check, _ := strconv.Atoi(calcStr[13:15])
	return int(97-(base%97)) == check
}

func BelgiumRrnValid(value string) bool {
	var digits strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	s := digits.String()
	if len(s) != 11 {
		return false
	}
	mm, _ := strconv.Atoi(s[2:4])
	dd, _ := strconv.Atoi(s[4:6])
	if mm < 1 || mm > 12 || dd < 1 || dd > 31 {
		return false
	}
	base9, _ := strconv.ParseInt(s[:9], 10, 64)
	check, _ := strconv.Atoi(s[9:11])
	if int(97-(base9%97)) == check {
		return true
	}
	base9_2000, _ := strconv.ParseInt("2"+s[:9], 10, 64)
	return int(97-(base9_2000%97)) == check
}

func FinlandHetuValid(value string) bool {
	s := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(s) != 11 {
		return false
	}
	dd, _ := strconv.Atoi(s[0:2])
	mm, _ := strconv.Atoi(s[2:4])
	yy, _ := strconv.Atoi(s[4:6])
	cent := s[6]
	if cent != '+' && cent != '-' && cent != 'A' {
		return false
	}
	ind := s[7:10]
	for _, r := range ind {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	year := 1800 + yy
	if cent == '-' {
		year = 1900 + yy
	} else if cent == 'A' {
		year = 2000 + yy
	}
	if !_isValidDate(year, mm, dd) {
		return false
	}
	seq := "0123456789ABCDEFHJKLMNPRSTUVWXY"
	numStr := s[0:6] + ind
	num, _ := strconv.ParseInt(numStr, 10, 64)
	return s[10] == seq[num%31]
}

func JpCorporateNumberValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if len(s) != 13 {
		return false
	}

	checkDigit := int(s[0] - '0')
	baseDigits := s[1:]

	total := 0
	for i := 0; i < 12; i++ {
		d := int(baseDigits[i] - '0')
		weight := 1
		if (12-i)%2 == 0 {
			weight = 2
		}
		total += d * weight
	}

	remainder := total % 9
	expectedCheck := 9 - remainder
	return checkDigit == expectedCheck
}

func TwUbnValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if len(s) != 8 {
		return false
	}

	weights := []int{1, 2, 1, 2, 1, 2, 4, 1}
	total := 0
	for i := 0; i < 8; i++ {
		prod := int(s[i]-'0') * weights[i]
		total += (prod / 10) + (prod % 10)
	}

	if total%10 == 0 {
		return true
	}
	if s[6] == '7' && (total+1)%10 == 0 {
		return true
	}
	return false
}

func UsNpiValid(value string) bool {
	var digitsOnly strings.Builder
	for _, r := range value {
		if unicode.IsDigit(r) {
			digitsOnly.WriteRune(r)
		}
	}
	s := digitsOnly.String()
	if len(s) != 10 {
		return false
	}

	fullStr := "80840" + s[:9]
	luhnTotal := 0
	for i := 0; i < len(fullStr); i++ {
		d := int(fullStr[len(fullStr)-1-i] - '0')
		if i%2 == 0 {
			d *= 2
			if d > 9 {
				d -= 9
			}
		}
		luhnTotal += d
	}

	expectedCheck := (10 - (luhnTotal % 10)) % 10
	return int(s[9]-'0') == expectedCheck
}

func UkNinoValid(value string) bool {
	val := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	match, _ := regexp.MatchString(`^[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]$`, val)
	if !match {
		return false
	}

	prefix := val[:2]
	excluded := []string{"BG", "GB", "KN", "NK", "NT", "TN", "ZZ"}
	for _, ex := range excluded {
		if prefix == ex {
			return false
		}
	}
	return true
}

func SwiftBicValid(value string) bool {
	val := strings.ToUpper(strings.ReplaceAll(value, " ", ""))
	if len(val) != 8 && len(val) != 11 {
		return false
	}
	match, _ := regexp.MatchString(`^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$`, val)
	return match
}

func AwsAccessKeyValid(value string) bool {
	if len(value) != 20 {
		return false
	}
	if !strings.HasPrefix(value, "AKIA") && !strings.HasPrefix(value, "ASIA") {
		return false
	}
	for _, r := range value {
		if !unicode.IsLetter(r) && !unicode.IsDigit(r) {
			return false
		}
	}
	return true
}

func GoogleApiKeyValid(value string) bool {
	if len(value) != 39 {
		return false
	}
	if !strings.HasPrefix(value, "AIza") {
		return false
	}
	match, _ := regexp.MatchString(`^[A-Za-z0-9_-]{39}$`, value)
	return match
}

func CryptoBtcValid(value string) bool {
	if len(value) < 26 || len(value) > 35 {
		return false
	}
	base58Chars := "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
	for _, r := range value {
		if !strings.ContainsRune(base58Chars, r) {
			return false
		}
	}
	return true
}

func CryptoEthValid(value string) bool {
	if len(value) != 42 {
		return false
	}
	if !strings.HasPrefix(value, "0x") {
		return false
	}
	match, _ := regexp.MatchString(`^0x[0-9a-fA-F]{40}$`, value)
	return match
}
