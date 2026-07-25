package com.piipatternengine.verification;

import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.function.Predicate;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Verification functions for additional validation after regex matching.
 * This class provides reusable verification functions that follow the same logic
 * as the Python implementation.
 */
public class Verification {
    private static final Logger LOGGER = Logger.getLogger(Verification.class.getName());

    private static final Map<String, Set<String>> DATA_CACHE = new HashMap<>();
    private static final Map<String, Predicate<String>> VERIFICATION_REGISTRY = new HashMap<>();

    // Common Chinese surnames (Simplified + Traditional)
    public static final Set<String> CHINESE_SURNAMES = new HashSet<>(Arrays.asList(
        "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "吴", "周", "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "高", "罗", "郑", "梁", "谢", "宋", "唐", "许", "邓", "冯", "韩", "曹", "曾", "彭", "萧", "蔡", "潘", "田", "董", "袁", "于", "余", "叶", "蒋", "杜", "苏", "魏", "程", "吕", "丁", "沈", "任", "姚", "卢", "傅", "钟", "姜", "崔", "谭", "廖", "范", "汪", "陆", "金", "石", "戴", "贾", "韦", "夏", "邱", "方", "侯", "邹", "熊", "孟", "秦", "白", "江", "阎", "薛", "尹", "段", "雷", "黎", "史", "龙", "陶", "贺", "顾", "毛", "郝", "龚", "邵", "万", "钱", "严", "赖", "覃", "洪", "武", "莫", "孔",
        "張", "劉", "陳", "楊", "黃", "趙", "吳", "許", "鄭", "謝", "鄧", "馮", "韓", "蕭", "葉", "蔣", "蘇", "魏", "呂", "瀋", "盧", "傅", "鐘", "薑", "譚", "廖", "範", "陸", "賈", "鄒", "閻", "龍", "陶", "賀", "顧", "郝", "龔", "萬", "錢", "嚴", "賴", "覃",
        "欧阳", "歐陽", "司马", "司馬", "上官", "诸葛", "諸葛", "东方", "東方", "皇甫", "尉迟", "尉遲", "公孙", "公孫", "令狐", "慕容", "轩辕", "軒轅", "夏侯", "司徒", "独孤", "獨孤"
    ));

    // Common Korean surnames
    public static final Set<String> KOREAN_SURNAMES = new HashSet<>(Arrays.asList(
        "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안", "송", "류", "유", "홍", "전", "고", "문", "양",
        "손", "배", "백", "허", "남", "심", "노", "하", "곽", "성", "차", "주", "우", "구", "민", "진", "나", "지", "엄", "변", "채", "원", "천", "방", "공", "현", "함", "염", "여", "추",
        "도", "소", "석", "선", "설", "마", "길", "연", "위", "표", "명", "기", "반", "왕", "금", "옥", "육", "인", "맹", "제", "모", "탁", "국", "어", "은", "편", "용", "예", "경", "봉", "사", "부", "황보", "남궁", "독고", "사공", "제갈", "선우"
    ));

    // Common Japanese surnames
    public static final Set<String> JAPANESE_SURNAMES = new HashSet<>(Arrays.asList(
        "佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤", "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "林", "斎藤", "清水", "山崎", "森", "阿部", "池田", "橋本", "山下", "石川", "中島", "前田", "藤田", "小川", "後藤", "岡田", "長谷川", "村上", "近藤", "石井", "斉藤", "坂本", "遠藤", "青木", "藤井", "西村", "福田", "太田", "三浦", "藤原", "岡本", "松田", "中川", "原田", "小野", "竹内", "金子", "和田", "中野", "原", "田村", "安藤", "河野", "上田", "大野", "高木", "工藤", "内田", "丸山", "今井", "酒井", "宮崎", "横山", "関", "堀", "島", "谷", "浜", "沢", "杉"
    ));

    // Chinese non-name keywords
    public static final Set<String> CHINESE_NON_NAME_KEYWORDS = new HashSet<>(Arrays.asList(
        "王国", "王朝", "王牌", "王者", "李子", "张开", "张力", "张贴", "黄金", "黄色", "黄油", "黄土", "黄瓜", "黄油", "黄河", "黄昏", "高度", "高级", "高中", "高速", "高考", "高峰", "高手", "高端", "周围", "周期", "周末", "周年", "周边", "周到", "马上", "马路", "马力", "朱红", "曹操", "白色", "白天", "白云", "白金", "白菜", "金属", "金融", "金额", "金钱", "金牌", "田地", "田野", "田园", "石头", "石油", "石材", "方法", "方案", "方向", "方式", "方面", "方便", "任务", "任何", "任意", "任命", "程度", "程序", "江山", "江南", "江河", "余额", "余下", "于是", "何时", "何处", "何必",
        "电话", "電話", "邮箱", "郵箱", "地址", "姓名", "信息", "資訊", "联系", "聯繫", "手机", "手機", "号码", "號碼", "传真", "傳真", "邮件", "郵件", "密码", "密碼", "账号", "帳號", "注册", "註冊", "登录", "登錄", "确认", "確認", "验证", "驗證", "性别", "性別", "生日", "职业", "職業", "公司", "部门", "部門"
    ));

    // Korean non-name keywords
    public static final Set<String> KOREAN_NON_NAME_KEYWORDS = new HashSet<>(Arrays.asList(
        "전화번호", "이메일", "연락처", "주소", "이름", "성명", "휴대폰", "핸드폰", "번호", "전화", "메일", "팩스", "모바일", "정보", "문의", "확인", "성별", "생년", "월일", "생일", "직업", "나이", "회사", "부서", "직책", "전화번", "메일주", "이메일주", "연락처는", "주소는", "이름은", "성명은"
    ));

    // Japanese non-name keywords
    public static final Set<String> JAPANESE_NON_NAME_KEYWORDS = new HashSet<>(Arrays.asList(
        "田園", "田畑", "田舎", "中心", "中央", "中間", "中古", "中止", "中国", "中学", "山脈", "山岳", "山林", "山地", "山頂", "高速", "高校", "高層", "高価", "高原", "高齢", "林業", "林道", "森林", "石油", "石材", "石炭", "石器", "金属", "金融", "金額", "金銭", "金庫", "上記", "上昇", "上手", "上司", "大学", "大会", "大臣", "大量", "大型", "大切", "大変", "小学", "小説", "小型", "小売", "原因", "原則", "原料", "原発", "内容", "内部", "内閣", "前回", "前者", "前提", "前日", "後半", "後者", "後日", "西洋", "西側", "青年", "青春", "近代", "近年", "近所", "遠方", "遠足", "池袋",
        "電話", "住所", "名前", "情報", "連絡", "番号", "携帯", "確認", "登録", "氏名", "性別", "生年", "職業", "会社", "部署", "郵便", "暗号", "認証", "口座"
    ));

    static {
        registerVerificationFunction("iban_mod97", Verification::ibanMod97);
        registerVerificationFunction("luhn", Verification::luhn);
        registerVerificationFunction("dms_coordinate", Verification::dmsCoordinate);
        registerVerificationFunction("high_entropy_token", Verification::highEntropyToken);
        registerVerificationFunction("not_timestamp", Verification::notTimestamp);
        registerVerificationFunction("korean_zipcode_valid", Verification::koreanZipcodeValid);
        registerVerificationFunction("us_zipcode_valid", Verification::usZipcodeValid);
        registerVerificationFunction("korean_bank_account_valid", Verification::koreanBankAccountValid);
        registerVerificationFunction("generic_number_not_timestamp", Verification::genericNumberNotTimestamp);
        registerVerificationFunction("contains_letter", Verification::containsLetter);
        registerVerificationFunction("us_ssn_valid", Verification::usSsnValid);
        registerVerificationFunction("cjk_name_standalone", Verification::cjkNameStandalone);
        registerVerificationFunction("chinese_name_valid", Verification::chineseNameValid);
        registerVerificationFunction("korean_name_valid", Verification::koreanNameValid);
        registerVerificationFunction("japanese_name_kanji_valid", Verification::japaneseNameKanjiValid);
        registerVerificationFunction("cn_national_id_valid", Verification::cnNationalIdValid);
        registerVerificationFunction("tw_national_id_valid", Verification::twNationalIdValid);
        registerVerificationFunction("india_aadhaar_valid", Verification::indiaAadhaarValid);
        registerVerificationFunction("india_pan_valid", Verification::indiaPanValid);
        registerVerificationFunction("kr_business_registration_valid", Verification::krBusinessRegistrationValid);
        registerVerificationFunction("ipv4_public", Verification::ipv4Public);
        registerVerificationFunction("not_repeating_pattern", Verification::notRepeatingPattern);
        registerVerificationFunction("credit_card_bin_valid", Verification::creditCardBinValid);
        registerVerificationFunction("kr_rrn_valid", Verification::krRrnValid);
        registerVerificationFunction("kr_alien_registration_valid", Verification::krAlienRegistrationValid);
        registerVerificationFunction("kr_corporate_registration_valid", Verification::krCorporateRegistrationValid);
        registerVerificationFunction("jp_zipcode_valid", Verification::jpZipcodeValid);
        registerVerificationFunction("cn_zipcode_valid", Verification::cnZipcodeValid);
        registerVerificationFunction("tw_zipcode_valid", Verification::twZipcodeValid);
        registerVerificationFunction("in_pincode_valid", Verification::inPincodeValid);
        registerVerificationFunction("jp_my_number_valid", Verification::jpMyNumberValid);
        registerVerificationFunction("spain_dni_valid", Verification::spainDniValid);
        registerVerificationFunction("spain_nie_valid", Verification::spainNieValid);
        registerVerificationFunction("netherlands_bsn_valid", Verification::netherlandsBsnValid);
        registerVerificationFunction("poland_pesel_valid", Verification::polandPeselValid);
        registerVerificationFunction("sweden_personnummer_valid", Verification::swedenPersonnummerValid);
        registerVerificationFunction("france_insee_valid", Verification::franceInseeValid);
        registerVerificationFunction("belgium_rrn_valid", Verification::belgiumRrnValid);
        registerVerificationFunction("finland_hetu_valid", Verification::finlandHetuValid);
        registerVerificationFunction("jp_corporate_number_valid", Verification::jpCorporateNumberValid);
        registerVerificationFunction("tw_ubn_valid", Verification::twUbnValid);
        registerVerificationFunction("us_npi_valid", Verification::usNpiValid);
        registerVerificationFunction("uk_nino_valid", Verification::ukNinoValid);
        registerVerificationFunction("swift_bic_valid", Verification::swiftBicValid);
        registerVerificationFunction("aws_access_key_valid", Verification::awsAccessKeyValid);
        registerVerificationFunction("google_api_key_valid", Verification::googleApiKeyValid);
        registerVerificationFunction("crypto_btc_valid", Verification::cryptoBtcValid);
        registerVerificationFunction("crypto_eth_valid", Verification::cryptoEthValid);
    }

    /**
     * Register a custom verification function.
     *
     * @param name Name to register the function under
     * @param func Verification function
     */
    public static void registerVerificationFunction(String name, Predicate<String> func) {
        VERIFICATION_REGISTRY.put(name, func);
        LOGGER.log(Level.INFO, "Registered verification function: {0}", name);
    }

    /**
     * Get verification function by name.
     *
     * @param name Name of verification function
     * @return Optional containing the verification function or empty if not found
     */
    public static Optional<Predicate<String>> getVerificationFunction(String name) {
        return Optional.ofNullable(VERIFICATION_REGISTRY.get(name));
    }

    private static Path getDataPath() {
        // Assume data is in ../../../../../../../../datas/ relative to this source or in project root/datas
        // Try to find datas folder in common locations
        Path current = Paths.get("").toAbsolutePath();
        Path datas = current.resolve("datas");
        if (Files.exists(datas)) {
            return datas;
        }
        // Try one level up
        datas = current.getParent().resolve("datas");
        if (Files.exists(datas)) {
            return datas;
        }
        return current.resolve("datas");
    }

    private static Set<String> loadDataFile(String filename) {
        if (DATA_CACHE.containsKey(filename)) {
            return DATA_CACHE.get(filename);
        }

        Set<String> values = new HashSet<>();
        Path dataPath = getDataPath().resolve(filename);

        if (Files.exists(dataPath)) {
            try {
                List<String> lines = Files.readAllLines(dataPath);
                if (lines.size() > 1) {
                    for (int i = 1; i < lines.size(); i++) {
                        String val = lines.get(i).trim();
                        if (!val.isEmpty()) {
                            values.add(val);
                        }
                    }
                }
                LOGGER.log(Level.INFO, "Loaded {0} entries from {1}", new Object[]{values.size(), filename});
            } catch (Exception e) {
                LOGGER.log(Level.SEVERE, "Failed to load data file " + filename, e);
            }
        }

        DATA_CACHE.put(filename, values);
        return values;
    }

    /**
     * Verify IBAN using Mod-97 check algorithm.
     */
    public static boolean ibanMod97(String value) {
        String iban = value.replace(" ", "").toUpperCase();
        if (iban.length() < 4) return false;

        String rearranged = iban.substring(4) + iban.substring(0, 4);
        StringBuilder numericString = new StringBuilder();

        for (char c : rearranged.toCharArray()) {
            if (Character.isDigit(c)) {
                numericString.append(c);
            } else if (Character.isLetter(c)) {
                numericString.append(c - 'A' + 10);
            } else {
                return false;
            }
        }

        try {
            BigInteger numeric = new BigInteger(numericString.toString());
            return numeric.remainder(BigInteger.valueOf(97)).intValue() == 1;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /**
     * Verify using Luhn algorithm (mod-10 checksum).
     */
    public static boolean luhn(String value) {
        List<Integer> digits = new ArrayList<>();
        for (char c : value.toCharArray()) {
            if (Character.isDigit(c)) {
                digits.add(Character.getNumericValue(c));
            }
        }

        if (digits.isEmpty()) return false;

        int checksum = 0;
        Collections.reverse(digits);

        for (int i = 0; i < digits.size(); i++) {
            int digit = digits.get(i);
            if (i % 2 == 1) {
                digit *= 2;
                if (digit > 9) {
                    digit -= 9;
                }
            }
            checksum += digit;
        }

        return checksum % 10 == 0;
    }

    /**
     * Verify DMS (Degrees Minutes Seconds) coordinate format.
     */
    public static boolean dmsCoordinate(String value) {
        Pattern pattern = Pattern.compile("(\\d{1,3})°\\s*(\\d{1,2})′\\s*(\\d{1,2}(?:\\.\\d+)?)″\\s*([NSEW])", Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(value);
        if (!matcher.find()) return false;

        int degrees = Integer.parseInt(matcher.group(1));
        int minutes = Integer.parseInt(matcher.group(2));
        double seconds = Double.parseDouble(matcher.group(3));
        String direction = matcher.group(4).toUpperCase();

        if (minutes > 59 || seconds >= 60) return false;

        if ("N".equals(direction) || "S".equals(direction)) {
            if (degrees > 90) return false;
        } else if ("E".equals(direction) || "W".equals(direction)) {
            if (degrees > 180) return false;
        }

        return true;
    }

    /**
     * Verify token has high entropy characteristics.
     */
    public static boolean highEntropyToken(String value) {
        if (value.length() < 20) return false;
        for (char c : value.toCharArray()) {
            if (c == ' ' || c == '\n' || c == '\r' || c == '\t') return false;
        }

        String allowedChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-+/.=";
        for (char c : value.toCharArray()) {
            if (allowedChars.indexOf(c) == -1) return false;
        }

        // Normalize for entropy calculation: lowercase and treat separators as spaces
        String normalized = value.toLowerCase().replace('-', ' ').replace('_', ' ');

        Map<Character, Integer> counts = new HashMap<>();
        for (char c : normalized.toCharArray()) {
            counts.put(c, counts.getOrDefault(c, 0) + 1);
        }

        double entropy = 0;
        double length = normalized.length();
        for (int count : counts.values()) {
            double p = count / length;
            entropy -= p * (Math.log(p) / Math.log(2));
        }

        return entropy >= 4.0;
    }

    /**
     * Verify that a numeric string is NOT a timestamp.
     */
    public static boolean notTimestamp(String value) {
        StringBuilder digitsOnlyBuilder = new StringBuilder();
        for (char c : value.toCharArray()) {
            if (Character.isDigit(c)) digitsOnlyBuilder.append(c);
        }
        String digitsOnly = digitsOnlyBuilder.toString();
        if (digitsOnly.isEmpty()) return true;

        int length = digitsOnly.length();

        if (length == 10) {
            try {
                long num = Long.parseLong(digitsOnly);
                if (num >= 1000000000L && num <= 9999999999L) return false;
            } catch (NumberFormatException e) {}
        }

        if (length == 13) {
            try {
                long num = Long.parseLong(digitsOnly);
                if (num >= 1000000000000L && num <= 9999999999999L) return false;
            } catch (NumberFormatException e) {}
        }

        if (length == 14) {
            try {
                int year = Integer.parseInt(digitsOnly.substring(0, 4));
                int month = Integer.parseInt(digitsOnly.substring(4, 6));
                int day = Integer.parseInt(digitsOnly.substring(6, 8));
                int hour = Integer.parseInt(digitsOnly.substring(8, 10));
                int minute = Integer.parseInt(digitsOnly.substring(10, 12));
                int second = Integer.parseInt(digitsOnly.substring(12, 14));

                if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31
                    && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59 && second >= 0 && second <= 59) {
                    return false;
                }
            } catch (Exception e) {}
        }

        return true;
    }

    /**
     * Verify Korean postal code is valid.
     */
    public static boolean koreanZipcodeValid(String value) {
        Set<String> validZips = loadDataFile("kr_zipcodes.csv");
        if (!validZips.isEmpty()) {
            return validZips.contains(value) || validZips.contains(value.replace("-", ""));
        }

        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() != 5) return false;

        boolean isSequentialUp = true;
        boolean isSequentialDown = true;
        for (int i = 1; i < digitsOnly.length(); i++) {
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) + 1) isSequentialUp = false;
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) - 1) isSequentialDown = false;
        }

        if (isSequentialUp || isSequentialDown) return false;

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        return true;
    }

    /**
     * Verify US postal code is valid.
     */
    public static boolean usZipcodeValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        Set<String> validZips = loadDataFile("us_zipcodes.csv");
        if (!validZips.isEmpty()) {
            if (digitsOnly.length() == 5) return validZips.contains(digitsOnly);
            else if (digitsOnly.length() == 9) return validZips.contains(digitsOnly.substring(0, 5));
        }

        if (digitsOnly.length() != 5 && digitsOnly.length() != 9) return false;

        String baseZip = digitsOnly.substring(0, 5);
        boolean isSequentialUp = true;
        boolean isSequentialDown = true;
        for (int i = 1; i < baseZip.length(); i++) {
            if (Character.getNumericValue(baseZip.charAt(i)) != Character.getNumericValue(baseZip.charAt(i - 1)) + 1) isSequentialUp = false;
            if (Character.getNumericValue(baseZip.charAt(i)) != Character.getNumericValue(baseZip.charAt(i - 1)) - 1) isSequentialDown = false;
        }
        if (isSequentialUp || isSequentialDown) return false;

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : baseZip.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        return true;
    }

    /**
     * Verify Japanese postal code is valid.
     */
    public static boolean jpZipcodeValid(String value) {
        String digitsOnly = value.replaceAll("[^0-9]", "");
        if (digitsOnly.length() != 7) return false;

        Set<String> validZips = loadDataFile("jp_zipcodes.csv");
        if (!validZips.isEmpty()) {
            String hyphenFormat = digitsOnly.substring(0, 3) + "-" + digitsOnly.substring(3);
            return validZips.contains(hyphenFormat) || validZips.contains(digitsOnly);
        }

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        boolean isSequentialUp = true;
        boolean isSequentialDown = true;
        for (int i = 1; i < digitsOnly.length(); i++) {
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) + 1) isSequentialUp = false;
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) - 1) isSequentialDown = false;
        }
        if (isSequentialUp || isSequentialDown) return false;

        return true;
    }

    /**
     * Verify Chinese postal code is valid.
     */
    public static boolean cnZipcodeValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() != 6) return false;

        Set<String> validZips = loadDataFile("cn_zipcodes.csv");
        if (!validZips.isEmpty()) return validZips.contains(digitsOnly);

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        boolean isSequentialUp = true;
        boolean isSequentialDown = true;
        for (int i = 1; i < digitsOnly.length(); i++) {
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) + 1) isSequentialUp = false;
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) - 1) isSequentialDown = false;
        }
        if (isSequentialUp || isSequentialDown) return false;

        int firstTwo = Integer.parseInt(digitsOnly.substring(0, 2));
        return firstTwo >= 1 && firstTwo <= 86;
    }

    /**
     * Verify Taiwan postal code is valid.
     */
    public static boolean twZipcodeValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() != 3 && digitsOnly.length() != 5) return false;

        Set<String> validZips = loadDataFile("tw_zipcodes.csv");
        if (!validZips.isEmpty()) {
            if (validZips.contains(digitsOnly)) return true;
            if (digitsOnly.length() == 5 && validZips.contains(digitsOnly.substring(0, 3))) return true;
            return false;
        }

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        int firstDigit = Character.getNumericValue(digitsOnly.charAt(0));
        return firstDigit != 0;
    }

    /**
     * Verify Indian PIN code is valid.
     */
    public static boolean inPincodeValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() != 6) return false;
        if (digitsOnly.charAt(0) == '0') return false;

        Set<String> validPins = loadDataFile("in_pincodes.csv");
        if (!validPins.isEmpty()) return validPins.contains(digitsOnly);

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        boolean isSequentialUp = true;
        boolean isSequentialDown = true;
        for (int i = 1; i < digitsOnly.length(); i++) {
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) + 1) isSequentialUp = false;
            if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) - 1) isSequentialDown = false;
        }
        if (isSequentialUp || isSequentialDown) return false;

        return true;
    }

    /**
     * Verify Korean bank account is valid and not a timestamp.
     */
    public static boolean koreanBankAccountValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.isEmpty()) return false;

        int length = digitsOnly.length();
        boolean hasKnownPrefix = false;
        String[] knownPrefixes = {"110", "120", "150", "190", "830", "1002", "301", "3333", "100"};
        for (String prefix : knownPrefixes) {
            if (digitsOnly.startsWith(prefix)) {
                hasKnownPrefix = true;
                break;
            }
        }

        if (hasKnownPrefix) {
            if (length == 10) {
                try {
                    long num = Long.parseLong(digitsOnly);
                    if (num >= 1600000000L && num <= 1800000000L) return false;
                } catch (NumberFormatException e) {}
            }
            return true;
        }

        if (length == 10) {
            try {
                long num = Long.parseLong(digitsOnly);
                if (num >= 1000000000L && num <= 9999999999L) return false;
            } catch (NumberFormatException e) {}
        }

        if (length == 13) {
            try {
                long num = Long.parseLong(digitsOnly);
                if (num >= 1000000000000L && num <= 9999999999999L) return false;
            } catch (NumberFormatException e) {}
        }

        if (length == 14) {
            try {
                int year = Integer.parseInt(digitsOnly.substring(0, 4));
                int month = Integer.parseInt(digitsOnly.substring(4, 6));
                int day = Integer.parseInt(digitsOnly.substring(6, 8));
                if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31) return false;
            } catch (Exception e) {}
        }

        if (length >= 10 && !hasKnownPrefix) {
            int maxSequential = 0;
            int currentSequential = 0;
            for (int i = 1; i < digitsOnly.length(); i++) {
                if (Character.getNumericValue(digitsOnly.charAt(i)) == Character.getNumericValue(digitsOnly.charAt(i - 1)) + 1) {
                    currentSequential++;
                    maxSequential = Math.max(maxSequential, currentSequential);
                } else {
                    currentSequential = 0;
                }
            }
            if (maxSequential >= 6) return false;
        }

        return true;
    }

    /**
     * Verify that a numeric string is likely NOT a timestamp (for generic patterns).
     */
    public static boolean genericNumberNotTimestamp(String value) {
        boolean hasSeparators = value.contains("-") || value.contains(" ") || value.contains("/");
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.isEmpty()) return true;

        int length = digitsOnly.length();

        if (hasSeparators) {
            if (length >= 14) {
                try {
                    int year = Integer.parseInt(digitsOnly.substring(0, 4));
                    int month = Integer.parseInt(digitsOnly.substring(4, 6));
                    int day = Integer.parseInt(digitsOnly.substring(6, 8));
                    if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31) return false;
                } catch (Exception e) {}
            }
            return true;
        }

        if (length == 10) {
            try {
                long num = Long.parseLong(digitsOnly);
                if (num >= 1000000000L && num <= 9999999999L) return false;
            } catch (NumberFormatException e) {}
        }

        if (length == 13) {
            try {
                long num = Long.parseLong(digitsOnly);
                if (num >= 1000000000000L && num <= 9999999999999L) return false;
            } catch (NumberFormatException e) {}
        }

        if (length >= 14) {
            try {
                int year = Integer.parseInt(digitsOnly.substring(0, 4));
                int month = Integer.parseInt(digitsOnly.substring(4, 6));
                int day = Integer.parseInt(digitsOnly.substring(6, 8));
                if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12 && day >= 1 && day <= 31) return false;
            } catch (Exception e) {}
        }

        return true;
    }

    /**
     * Verify that the value contains at least one letter.
     */
    public static boolean containsLetter(String value) {
        for (char c : value.toCharArray()) {
            if (Character.isLetter(c)) return true;
        }
        return false;
    }

    /**
     * Verify US SSN is valid.
     */
    public static boolean usSsnValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 9) return false;

        int area = Integer.parseInt(digits.substring(0, 3));
        int group = Integer.parseInt(digits.substring(3, 5));
        int serial = Integer.parseInt(digits.substring(5, 9));

        if (area == 0 || area == 666 || area >= 900) return false;
        if (group == 0) return false;
        if (serial == 0) return false;

        return true;
    }

    /**
     * Verify Chinese name has a valid surname prefix and given name.
     */
    public static boolean chineseNameValid(String value) {
        if (value == null || value.length() < 2 || value.length() > 4) return false;
        if (CHINESE_NON_NAME_KEYWORDS.contains(value)) return false;

        String surname = null;
        String givenName = null;

        if (value.length() >= 3 && CHINESE_SURNAMES.contains(value.substring(0, 2))) {
            surname = value.substring(0, 2);
            givenName = value.substring(2);
        } else if (CHINESE_SURNAMES.contains(value.substring(0, 1))) {
            surname = value.substring(0, 1);
            givenName = value.substring(1);
        }

        if (surname == null) return false;

        Set<String> validGivenNames = loadDataFile("cn_given_names.csv");
        if (!validGivenNames.isEmpty() && validGivenNames.contains(givenName)) return true;

        return value.length() >= 2 && value.length() <= 4;
    }

    /**
     * Verify Korean name has a valid surname prefix and is not a common keyword.
     */
    public static boolean koreanNameValid(String value) {
        if (value == null || value.length() < 2 || value.length() > 5) return false;
        if (KOREAN_NON_NAME_KEYWORDS.contains(value)) return false;

        String particles = "은는이가을를의";
        if (value.length() >= 3 && particles.indexOf(value.charAt(value.length() - 1)) != -1) {
            if (KOREAN_NON_NAME_KEYWORDS.contains(value.substring(0, value.length() - 1))) return false;
        }

        String surname = null;
        String givenName = null;

        if (value.length() >= 3 && KOREAN_SURNAMES.contains(value.substring(0, 2))) {
            surname = value.substring(0, 2);
            givenName = value.substring(2);
        } else if (KOREAN_SURNAMES.contains(value.substring(0, 1))) {
            surname = value.substring(0, 1);
            givenName = value.substring(1);
        }

        if (surname == null) return false;

        Set<String> validGivenNames = loadDataFile("kr_given_names.csv");
        if (!validGivenNames.isEmpty() && validGivenNames.contains(givenName)) return true;

        return value.length() == 3;
    }

    /**
     * Verify Japanese name (kanji) matches known surname patterns and given name.
     */
    public static boolean japaneseNameKanjiValid(String value) {
        if (value == null || value.length() < 2 || value.length() > 6) return false;
        if (JAPANESE_NON_NAME_KEYWORDS.contains(value)) return false;

        if (value.length() == 2) return JAPANESE_SURNAMES.contains(value);

        String surname = null;
        String givenName = null;

        if (value.length() >= 4 && JAPANESE_SURNAMES.contains(value.substring(0, 3))) {
            surname = value.substring(0, 3);
            givenName = value.substring(3);
        } else if (value.length() >= 2 && JAPANESE_SURNAMES.contains(value.substring(0, 2))) {
            surname = value.substring(0, 2);
            givenName = value.substring(2);
        } else if (JAPANESE_SURNAMES.contains(value.substring(0, 1))) {
            surname = value.substring(0, 1);
            givenName = value.substring(1);
        }

        if (surname == null) return false;

        Set<String> validGivenNames = loadDataFile("jp_given_names.csv");
        if (!validGivenNames.isEmpty() && validGivenNames.contains(givenName)) return true;

        return value.length() == 3 || value.length() == 4;
    }

    /**
     * Verify that a CJK name match is standalone (expected length for a name).
     */
    public static boolean cjkNameStandalone(String value) {
        if (value == null || value.isEmpty() || value.length() > 6) return false;

        for (char c : value.toCharArray()) {
            int code = (int) c;
            boolean isCjk = (code >= 0x4E00 && code <= 0x9FFF) // CJK Unified Ideographs
                || (code >= 0xAC00 && code <= 0xD7AF) // Korean Hangul
                || (code >= 0x3040 && code <= 0x309F) // Hiragana
                || (code >= 0x30A0 && code <= 0x30FF); // Katakana
            if (!isCjk) return false;
        }

        return true;
    }

    /**
     * Verify Chinese National ID (18 digits) using checksum algorithm.
     */
    public static boolean cnNationalIdValid(String value) {
        String idStr = value.replace(" ", "").toUpperCase();
        if (idStr.length() != 18) return false;

        String[] validProvinces = {
            "11", "12", "13", "14", "15", "21", "22", "23", "31", "32", "33", "34", "35", "36", "37",
            "41", "42", "43", "44", "45", "46", "50", "51", "52", "53", "54", "61", "62", "63", "64", "65",
            "71", "81", "82", "91"
        };
        boolean provinceValid = false;
        String pCode = idStr.substring(0, 2);
        for (String p : validProvinces) {
            if (p.equals(pCode)) {
                provinceValid = true;
                break;
            }
        }
        if (!provinceValid) return false;

        try {
            int year = Integer.parseInt(idStr.substring(6, 10));
            int month = Integer.parseInt(idStr.substring(10, 12));
            int day = Integer.parseInt(idStr.substring(12, 14));
            if (!_isValidDate(year, month, day)) return false;
        } catch (Exception e) {
            return false;
        }

        int[] weights = {7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2};
        String[] checkDigits = {"1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"};

        try {
            int total = 0;
            for (int i = 0; i < 17; i++) {
                total += Character.getNumericValue(idStr.charAt(i)) * weights[i];
            }
            String expectedCheck = checkDigits[total % 11];
            return idStr.substring(17).equals(expectedCheck);
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Verify Taiwan National ID using checksum algorithm.
     */
    public static boolean twNationalIdValid(String value) {
        String idStr = value.replace(" ", "").toUpperCase();
        if (idStr.length() != 10) return false;
        if (!Character.isLetter(idStr.charAt(0))) return false;

        for (int i = 1; i < 10; i++) {
            if (!Character.isDigit(idStr.charAt(i))) return false;
        }

        char firstChar = idStr.charAt(0);
        if (firstChar == 'I' || firstChar == 'O' || firstChar == 'W') return false;

        int letterCode = firstChar - 'A' + 10;
        int gender = Character.getNumericValue(idStr.charAt(1));
        if (gender != 1 && gender != 2) return false;

        int firstDigit = letterCode / 10;
        int secondDigit = letterCode % 10;
        int total = firstDigit * 1 + secondDigit * 9;

        int[] weights = {8, 7, 6, 5, 4, 3, 2, 1};
        for (int i = 0; i < weights.length; i++) {
            total += Character.getNumericValue(idStr.charAt(i + 1)) * weights[i];
        }
        total += Character.getNumericValue(idStr.charAt(9));

        return total % 10 == 0;
    }

    /**
     * Verify India Aadhaar number using Verhoeff checksum algorithm.
     */
    public static boolean indiaAadhaarValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() != 12) return false;
        if (digitsOnly.charAt(0) == '0' || digitsOnly.charAt(0) == '1') return false;

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        int[][] d = {
            {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}, {1, 2, 3, 4, 0, 6, 7, 8, 9, 5}, {2, 3, 4, 0, 1, 7, 8, 9, 5, 6},
            {3, 4, 0, 1, 2, 8, 9, 5, 6, 7}, {4, 0, 1, 2, 3, 9, 5, 6, 7, 8}, {5, 9, 8, 7, 6, 0, 4, 3, 2, 1},
            {6, 5, 9, 8, 7, 1, 0, 4, 3, 2}, {7, 6, 5, 9, 8, 2, 1, 0, 4, 3}, {8, 7, 6, 5, 9, 3, 2, 1, 0, 4},
            {9, 8, 7, 6, 5, 4, 3, 2, 1, 0}
        };
        int[][] p = {
            {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}, {1, 5, 7, 6, 2, 8, 3, 0, 9, 4}, {5, 8, 0, 3, 7, 9, 6, 1, 4, 2},
            {8, 9, 1, 6, 0, 4, 3, 5, 2, 7}, {9, 4, 5, 3, 1, 2, 6, 8, 7, 0}, {4, 2, 8, 6, 5, 7, 3, 9, 0, 1},
            {2, 7, 9, 3, 8, 0, 6, 4, 1, 5}, {7, 0, 4, 6, 9, 1, 3, 2, 5, 8}
        };

        int c = 0;
        String reversed = new StringBuilder(digitsOnly).reverse().toString();
        for (int i = 0; i < reversed.length(); i++) {
            c = d[c][p[i % 8][Character.getNumericValue(reversed.charAt(i))]];
        }
        return c == 0;
    }

    /**
     * Verify India PAN (Permanent Account Number) format.
     */
    public static boolean indiaPanValid(String value) {
        String pan = value.replace(" ", "").toUpperCase();
        if (pan.length() != 10) return false;

        for (int i = 0; i < 5; i++) if (!Character.isLetter(pan.charAt(i))) return false;
        for (int i = 5; i < 9; i++) if (!Character.isDigit(pan.charAt(i))) return false;
        if (!Character.isLetter(pan.charAt(9))) return false;

        String validEntities = "ABCFGHKLPTJ";
        if (validEntities.indexOf(pan.charAt(3)) == -1) return false;

        String prefix = pan.substring(0, 5);
        if (prefix.equals("AAAAA") || prefix.equals("ABCDE") || prefix.equals("XXXXX") || prefix.equals("ZZZZZ")) return false;

        return true;
    }

    /**
     * Verify Korean Business Registration Number (사업자등록번호) checksum.
     */
    public static boolean krBusinessRegistrationValid(String value) {
        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() != 10) return false;

        Set<Character> distinctDigits = new HashSet<>();
        for (char c : digitsOnly.toCharArray()) distinctDigits.add(c);
        if (distinctDigits.size() == 1) return false;

        int[] weights = {1, 3, 7, 1, 3, 7, 1, 3, 5};
        int total = 0;
        for (int i = 0; i < 9; i++) {
            int digit = Character.getNumericValue(digitsOnly.charAt(i));
            total += digit * weights[i];
            if (i == 8) {
                total += (digit * 5) / 10;
            }
        }

        int checkDigit = (10 - (total % 10)) % 10;
        return Character.getNumericValue(digitsOnly.charAt(9)) == checkDigit;
    }

    /**
     * Verify IPv4 address is a public (routable) address.
     */
    public static boolean ipv4Public(String value) {
        try {
            String[] parts = value.split("\\.");
            if (parts.length != 4) return false;

            int[] octets = new int[4];
            for (int i = 0; i < 4; i++) {
                octets[i] = Integer.parseInt(parts[i]);
                if (octets[i] < 0 || octets[i] > 255) return false;
            }

            int first = octets[0];
            int second = octets[1];
            int third = octets[2];

            if (first == 0) return false;
            if (first == 10) return false;
            if (first == 127) return false;
            if (first == 169 && second == 254) return false;
            if (first == 172 && second >= 16 && second <= 31) return false;
            if (first == 192 && second == 0 && third == 2) return false;
            if (first == 192 && second == 168) return false;
            if (first == 198 && second == 51 && third == 100) return false;
            if (first == 203 && second == 0 && third == 113) return false;
            if (first >= 224 && first <= 239) return false;
            if (first >= 240) return false;

            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Verify that a value is not a simple repeating pattern.
     */
    public static boolean notRepeatingPattern(String value) {
        if (value == null || value.length() < 4) return true;

        Set<Character> distinct = new HashSet<>();
        for (char c : value.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        String digitsOnly = value.replaceAll("\\D", "");
        if (digitsOnly.length() >= 4) {
            boolean isAscending = true;
            boolean isDescending = true;
            for (int i = 1; i < digitsOnly.length(); i++) {
                if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) + 1) isAscending = false;
                if (Character.getNumericValue(digitsOnly.charAt(i)) != Character.getNumericValue(digitsOnly.charAt(i - 1)) - 1) isDescending = false;
            }
            if (isAscending || isDescending) return false;
        }

        if (value.length() >= 4) {
            String pattern2 = value.substring(0, 2);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < value.length() / 2; i++) sb.append(pattern2);
            String repeated = sb.toString();
            if (value.startsWith(repeated)) {
                int rem = value.length() % 2;
                if (rem == 0 || value.endsWith(pattern2.substring(0, rem))) return false;
            }
        }

        if (value.length() >= 6) {
            String pattern3 = value.substring(0, 3);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < value.length() / 3; i++) sb.append(pattern3);
            String repeated = sb.toString();
            if (value.startsWith(repeated)) {
                int rem = value.length() % 3;
                if (rem == 0 || value.endsWith(pattern3.substring(0, rem))) return false;
            }
        }

        return true;
    }

    /**
     * Verify credit card number has valid BIN (Bank Identification Number) prefix.
     */
    public static boolean creditCardBinValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() < 13 || digits.length() > 19) return false;

        boolean validBin = false;
        if (digits.startsWith("4")) validBin = true;
        else if (digits.length() >= 2) {
            int p2 = Integer.parseInt(digits.substring(0, 2));
            if (p2 >= 51 && p2 <= 55) validBin = true;
            else if (digits.length() >= 4) {
                int p4 = Integer.parseInt(digits.substring(0, 4));
                if (p4 >= 2221 && p4 <= 2720) validBin = true;
            }
        }

        if (!validBin && digits.length() >= 2) {
            int p2 = Integer.parseInt(digits.substring(0, 2));
            if (p2 == 34 || p2 == 37) validBin = true;
        }

        if (!validBin) {
            if (digits.startsWith("6011") || digits.startsWith("65")) validBin = true;
            else if (digits.length() >= 3) {
                int p3 = Integer.parseInt(digits.substring(0, 3));
                if (p3 >= 644 && p3 <= 649) validBin = true;
            }
            if (!validBin && digits.length() >= 6) {
                int p6 = Integer.parseInt(digits.substring(0, 6));
                if (p6 >= 622126 && p6 <= 622925) validBin = true;
            }
        }

        if (!validBin && digits.length() >= 4) {
            int p4 = Integer.parseInt(digits.substring(0, 4));
            if (p4 >= 3528 && p4 <= 3589) validBin = true;
        }

        if (!validBin && digits.startsWith("62")) validBin = true;

        if (!validBin && digits.length() >= 2) {
            int p2 = Integer.parseInt(digits.substring(0, 2));
            if (p2 == 36 || p2 == 38) validBin = true;
            else if (digits.length() >= 3) {
                int p3 = Integer.parseInt(digits.substring(0, 3));
                if (p3 >= 300 && p3 <= 305) validBin = true;
            }
        }

        if (!validBin) return false;
        return luhn(digits);
    }

    private static boolean _isValidDate(int year, int month, int day) {
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;

        int[] daysInMonth = {0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
        if (day > daysInMonth[month]) return false;

        if (month == 2 && day == 29) {
            boolean isLeap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
            if (!isLeap) return false;
        }

        return true;
    }

    /**
     * Verify Korean Resident Registration Number (주민등록번호).
     */
    public static boolean krRrnValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 13) return false;

        try {
            int yy = Integer.parseInt(digits.substring(0, 2));
            int mm = Integer.parseInt(digits.substring(2, 4));
            int dd = Integer.parseInt(digits.substring(4, 6));
            int gc = Character.getNumericValue(digits.charAt(6));

            if (gc < 1 || gc > 4) return false;
            int year = (gc <= 2) ? 1900 + yy : 2000 + yy;
            if (!_isValidDate(year, mm, dd)) return false;
        } catch (Exception e) {
            return false;
        }

        Set<Character> distinct = new HashSet<>();
        for (char c : digits.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        int[] weights = {2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5};
        int total = 0;
        for (int i = 0; i < 12; i++) {
            total += Character.getNumericValue(digits.charAt(i)) * weights[i];
        }
        int checkDigit = (11 - (total % 11)) % 10;
        return Character.getNumericValue(digits.charAt(12)) == checkDigit;
    }

    /**
     * Verify Korean Alien Registration Number (외국인등록번호).
     */
    public static boolean krAlienRegistrationValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 13) return false;

        try {
            int yy = Integer.parseInt(digits.substring(0, 2));
            int mm = Integer.parseInt(digits.substring(2, 4));
            int dd = Integer.parseInt(digits.substring(4, 6));
            int gc = Character.getNumericValue(digits.charAt(6));

            if (gc < 5 || gc > 8) return false;
            int year = (gc <= 6) ? 1900 + yy : 2000 + yy;
            if (!_isValidDate(year, mm, dd)) return false;
        } catch (Exception e) {
            return false;
        }

        Set<Character> distinct = new HashSet<>();
        for (char c : digits.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        return true;
    }

    /**
     * Verify Japanese My Number (マイナンバー) checksum.
     */
    public static boolean jpMyNumberValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 12) return false;

        Set<Character> distinct = new HashSet<>();
        for (char c : digits.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        if (digits.equals("123456789012") || digits.equals("012345678901")) return false;

        int[] weights = {6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2};
        int total = 0;
        for (int i = 0; i < 11; i++) {
            total += Character.getNumericValue(digits.charAt(i)) * weights[i];
        }
        int remainder = total % 11;
        int expectedCheck = (remainder <= 1) ? 0 : 11 - remainder;
        return Character.getNumericValue(digits.charAt(11)) == expectedCheck;
    }

    /**
     * Verify Korean Corporate Registration Number (법인등록번호) checksum.
     */
    public static boolean krCorporateRegistrationValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 13) return false;

        Set<Character> distinct = new HashSet<>();
        for (char c : digits.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        int[] weights = {1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2};
        int total = 0;
        for (int i = 0; i < 12; i++) {
            int product = Character.getNumericValue(digits.charAt(i)) * weights[i];
            if (product > 9) product -= 9;
            total += product;
        }
        int checkDigit = (10 - (total % 10)) % 10;
        return Character.getNumericValue(digits.charAt(12)) == checkDigit;
    }

    /**
     * Verify Spanish DNI (Documento Nacional de Identidad) checksum.
     */
    public static boolean spainDniValid(String value) {
        String dni = value.replace(" ", "").toUpperCase();
        if (dni.length() != 9) return false;
        if (!dni.substring(0, 8).matches("\\d{8}")) return false;
        if (!Character.isLetter(dni.charAt(8))) return false;

        String letters = "TRWAGMYFPDXBNJZSQVHLCKE";
        long number = Long.parseLong(dni.substring(0, 8));
        char expectedLetter = letters.charAt((int) (number % 23));
        return dni.charAt(8) == expectedLetter;
    }

    /**
     * Verify Spanish NIE (Número de Identidad de Extranjero) checksum.
     */
    public static boolean spainNieValid(String value) {
        String nie = value.replace(" ", "").toUpperCase();
        if (nie.length() != 9) return false;
        if ("XYZ".indexOf(nie.charAt(0)) == -1) return false;
        if (!nie.substring(1, 8).matches("\\d{7}")) return false;
        if (!Character.isLetter(nie.charAt(8))) return false;

        String replacements = "012";
        String numberStr = replacements.charAt("XYZ".indexOf(nie.charAt(0))) + nie.substring(1, 8);
        String letters = "TRWAGMYFPDXBNJZSQVHLCKE";
        long number = Long.parseLong(numberStr);
        char expectedLetter = letters.charAt((int) (number % 23));
        return nie.charAt(8) == expectedLetter;
    }

    /**
     * Verify Dutch BSN (Burgerservicenummer) using 11-proof algorithm.
     */
    public static boolean netherlandsBsnValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() == 8) digits = "0" + digits;
        else if (digits.length() != 9) return false;

        Set<Character> distinct = new HashSet<>();
        for (char c : digits.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        int[] weights = {9, 8, 7, 6, 5, 4, 3, 2, -1};
        int total = 0;
        for (int i = 0; i < 9; i++) {
            total += Character.getNumericValue(digits.charAt(i)) * weights[i];
        }
        return total % 11 == 0;
    }

    /**
     * Verify Polish PESEL checksum.
     */
    public static boolean polandPeselValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 11) return false;

        Set<Character> distinct = new HashSet<>();
        for (char c : digits.toCharArray()) distinct.add(c);
        if (distinct.size() == 1) return false;

        try {
            int yy = Integer.parseInt(digits.substring(0, 2));
            int mm = Integer.parseInt(digits.substring(2, 4));
            int dd = Integer.parseInt(digits.substring(4, 6));

            int year, month;
            if (mm >= 1 && mm <= 12) { year = 1900 + yy; month = mm; }
            else if (mm >= 21 && mm <= 32) { year = 2000 + yy; month = mm - 20; }
            else if (mm >= 41 && mm <= 52) { year = 2100 + yy; month = mm - 40; }
            else if (mm >= 61 && mm <= 72) { year = 2200 + yy; month = mm - 60; }
            else if (mm >= 81 && mm <= 92) { year = 1800 + yy; month = mm - 80; }
            else return false;

            if (!_isValidDate(year, month, dd)) return false;
        } catch (Exception e) { return false; }

        int[] weights = {1, 3, 7, 9, 1, 3, 7, 9, 1, 3};
        int total = 0;
        for (int i = 0; i < 10; i++) {
            total += Character.getNumericValue(digits.charAt(i)) * weights[i];
        }
        int checkDigit = (10 - (total % 10)) % 10;
        return Character.getNumericValue(digits.charAt(10)) == checkDigit;
    }

    /**
     * Verify Swedish Personnummer using Luhn algorithm.
     */
    public static boolean swedenPersonnummerValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() == 12) digits = digits.substring(2);
        else if (digits.length() != 10) return false;

        try {
            int mm = Integer.parseInt(digits.substring(2, 4));
            int dd = Integer.parseInt(digits.substring(4, 6));
            if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return false;
        } catch (Exception e) { return false; }

        return luhn(digits);
    }

    /**
     * Verify French INSEE/NIR number (Numéro de Sécurité Sociale).
     */
    public static boolean franceInseeValid(String value) {
        String cleaned = value.replace(" ", "");
        if (cleaned.length() != 15) return false;

        String calcStr = cleaned;
        if (cleaned.substring(5, 7).equalsIgnoreCase("2A")) {
            calcStr = cleaned.substring(0, 5) + "19" + cleaned.substring(7);
        } else if (cleaned.substring(5, 7).equalsIgnoreCase("2B")) {
            calcStr = cleaned.substring(0, 5) + "18" + cleaned.substring(7);
        }

        if (!calcStr.matches("\\d{15}")) return false;

        int sex = Character.getNumericValue(calcStr.charAt(0));
        if (sex != 1 && sex != 2) return false;

        int month = Integer.parseInt(calcStr.substring(3, 5));
        if (month < 1 || month > 12) return false;

        BigInteger baseNumber = new BigInteger(calcStr.substring(0, 13));
        int expectedCheck = 97 - baseNumber.remainder(BigInteger.valueOf(97)).intValue();
        int actualCheck = Integer.parseInt(calcStr.substring(13, 15));

        return actualCheck == expectedCheck;
    }

    /**
     * Verify Belgian Rijksregisternummer (National Register Number).
     */
    public static boolean belgiumRrnValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 11) return false;

        try {
            int mm = Integer.parseInt(digits.substring(2, 4));
            int dd = Integer.parseInt(digits.substring(4, 6));
            if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return false;
        } catch (Exception e) { return false; }

        long base9 = Long.parseLong(digits.substring(0, 9));
        int checkDigits = Integer.parseInt(digits.substring(9, 11));

        if (checkDigits == 97 - (int) (base9 % 97)) return true;

        long base9_2000 = Long.parseLong("2" + digits.substring(0, 9));
        return checkDigits == 97 - (int) (base9_2000 % 97);
    }

    /**
     * Verify Finnish HETU (Henkilötunnus).
     */
    public static boolean finlandHetuValid(String value) {
        String hetu = value.replace(" ", "").toUpperCase();
        if (hetu.length() != 11) return false;

        try {
            int dd = Integer.parseInt(hetu.substring(0, 2));
            int mm = Integer.parseInt(hetu.substring(2, 4));
            int yy = Integer.parseInt(hetu.substring(4, 6));
            char centurySign = hetu.charAt(6);
            String individual = hetu.substring(7, 10);
            char checkChar = hetu.charAt(10);

            if ("+-A".indexOf(centurySign) == -1) return false;
            if (!individual.matches("\\d{3}")) return false;

            int year = (centurySign == '+') ? 1800 + yy : (centurySign == '-') ? 1900 + yy : 2000 + yy;
            if (!_isValidDate(year, mm, dd)) return false;

            String checkSequence = "0123456789ABCDEFHJKLMNPRSTUVWXY";
            long number = Long.parseLong(hetu.substring(0, 6) + individual);
            char expectedCheck = checkSequence.charAt((int) (number % 31));

            return checkChar == expectedCheck;
        } catch (Exception e) { return false; }
    }

    /**
     * Verify Japanese Corporate Number checksum.
     */
    public static boolean jpCorporateNumberValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 13) return false;

        int checkDigit = Character.getNumericValue(digits.charAt(0));
        String baseDigits = digits.substring(1);

        int total = 0;
        for (int i = 0; i < 12; i++) {
            int d = Character.getNumericValue(baseDigits.charAt(i));
            int weight = (12 - i) % 2 == 0 ? 2 : 1;
            total += d * weight;
        }

        int remainder = total % 9;
        int expectedCheck = 9 - remainder;
        return checkDigit == expectedCheck;
    }

    /**
     * Verify Taiwan Unified Business Number (UBN).
     */
    public static boolean twUbnValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 8) return false;

        int[] weights = {1, 2, 1, 2, 1, 2, 4, 1};
        int total = 0;
        for (int i = 0; i < 8; i++) {
            int prod = Character.getNumericValue(digits.charAt(i)) * weights[i];
            total += (prod / 10) + (prod % 10);
        }

        if (total % 10 == 0) return true;
        if (digits.charAt(6) == '7' && (total + 1) % 10 == 0) return true;

        return false;
    }

    /**
     * Verify US National Provider Identifier (NPI).
     */
    public static boolean usNpiValid(String value) {
        String digits = value.replaceAll("\\D", "");
        if (digits.length() != 10) return false;

        String fullStr = "80840" + digits.substring(0, 9);
        int luhnTotal = 0;
        for (int i = 0; i < fullStr.length(); i++) {
            int d = Character.getNumericValue(fullStr.charAt(fullStr.length() - 1 - i));
            if (i % 2 == 0) {
                d *= 2;
                if (d > 9) d -= 9;
            }
            luhnTotal += d;
        }

        int expectedCheck = (10 - (luhnTotal % 10)) % 10;
        return Character.getNumericValue(digits.charAt(9)) == expectedCheck;
    }

    /**
     * Verify UK National Insurance Number (NINO).
     */
    public static boolean ukNinoValid(String value) {
        String val = value.replace(" ", "").toUpperCase();
        if (!val.matches("^[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\\d{6}[A-D]$")) return false;

        String prefix = val.substring(0, 2);
        List<String> excluded = Arrays.asList("BG", "GB", "KN", "NK", "NT", "TN", "ZZ");
        return !excluded.contains(prefix);
    }

    /**
     * Verify SWIFT/BIC code.
     */
    public static boolean swiftBicValid(String value) {
        String val = value.replace(" ", "").toUpperCase();
        if (val.length() != 8 && val.length() != 11) return false;
        return val.matches("^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$");
    }

    /**
     * Verify AWS Access Key.
     */
    public static boolean awsAccessKeyValid(String value) {
        if (value.length() != 20) return false;
        if (!value.startsWith("AKIA") && !value.startsWith("ASIA")) return false;
        return value.matches("^[A-Z0-9]+$");
    }

    /**
     * Verify Google API Key.
     */
    public static boolean googleApiKeyValid(String value) {
        if (value.length() != 39) return false;
        if (!value.startsWith("AIza")) return false;
        return value.matches("^[A-Za-z0-9_-]{39}$");
    }

    /**
     * Verify Bitcoin address.
     */
    public static boolean cryptoBtcValid(String value) {
        if (value.length() < 26 || value.length() > 35) return false;
        return value.matches("^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$");
    }

    /**
     * Verify Ethereum address.
     */
    public static boolean cryptoEthValid(String value) {
        if (value.length() != 42) return false;
        if (!value.startsWith("0x")) return false;
        return value.matches("^0x[0-9a-fA-F]{40}$");
    }
}
