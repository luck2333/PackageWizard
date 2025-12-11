import pandas as pd
import re
import numpy as np
import sys

# ==========================================
# 1. 配置列映射关系
# ==========================================
COLUMN_MAPPING = {
    'PDF名称': 'PDF名称',
    '页码': '页码',
    '封装类型': 'package_type',
    'Pitch x (el)': 'Pitch x (el)',
    'Pitch y (e)': 'Pitch y (e)',
    'Number of pins along X': 'Number of pins along X',
    'Number of pins along Y': 'Number of pins along Y',
    'Package Height (A)': 'Package Height (A)',
    'Standoff (A1)': 'Standoff (A1)',
    'Body X (D)': 'Body X (D)',
    'Body Y (E)': 'Body Y (E)',
    'Edge Fillet Radius': 'Edge Fillet Radius',
    'Ball Diameter Normal (b)': 'Ball Diameter Normal (b)',
    'Exclude Pins': 'Exclude Pins'
}

LIST_COLUMNS = [
    'Pitch x (el)', 'Pitch y (e)', 'Number of pins along X',
    'Number of pins along Y', 'Package Height (A)', 'Standoff (A1)',
    'Body X (D)', 'Body Y (E)', 'Edge Fillet Radius',
    'Ball Diameter Normal (b)'
]


# ==========================================
# 2. 数据清洗函数
# ==========================================

def normalize_filename(name):
    if pd.isna(name): return ""
    name = str(name).lower()
    name = name.replace('.pdf', '')
    return re.sub(r'[^a-z0-9]', '', name)


def parse_list_string(val):
    if pd.isna(val) or str(val).strip() == '':
        return [None, None, None]
    clean_str = str(val).replace('[', '').replace(']', '').replace("'", "").replace('"', "")
    parts = clean_str.split(',')
    result = []
    for p in parts:
        p_str = p.strip()
        if p_str == '' or p_str.lower() == 'none' or p_str.lower() == 'nan':
            result.append(None)
        else:
            try:
                result.append(float(p_str))
            except ValueError:
                result.append(p_str)
    if len(result) == 0: return [None, None, None]
    return result


def parse_exclude_pins(val):
    if pd.isna(val) or str(val).strip() == '': return set()
    if "None" in str(val) and "[]" in str(val): return set()
    clean_str = str(val).replace('[', '').replace(']', '').replace("'", "").replace('"', "")
    parts = clean_str.split(',')
    pins = set()
    for p in parts:
        p_str = p.strip().upper()
        if p_str and p_str not in ['NONE', 'NAN', '']:
            pins.add(p_str)
    return pins


def normalize_text(val):
    if pd.isna(val): return ""
    return str(val).strip().upper()


def compare_values(std_val, res_val, col_name):
    if col_name == 'Exclude Pins':
        return std_val == res_val
    if isinstance(std_val, list) and isinstance(res_val, list):
        if len(std_val) != len(res_val): return False
        for v1, v2 in zip(std_val, res_val):
            if v1 is None and v2 is None: continue
            if v1 is None or v2 is None: return False
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                if abs(v1 - v2) > 0.001: return False
            else:
                if str(v1) != str(v2): return False
        return True
    return str(std_val) == str(res_val)


# ==========================================
# 3. 读取文件的辅助函数 (核心修复)
# ==========================================
def read_csv_smart(filename):
    """尝试不同的编码和引擎读取CSV"""
    encodings = ['utf-8-sig', 'gbk', 'utf-16']

    for enc in encodings:
        try:
            # 使用 python 引擎解析，对引号包裹的列表支持更好
            df = pd.read_csv(filename, encoding=enc, engine='python', on_bad_lines='skip')

            # 简单检查：如果有'页码'列，且第一行不是长得像列表的东西
            if '页码' in df.columns and len(df) > 0:
                first_page_val = str(df.iloc[0]['页码'])
                if '[' not in first_page_val:  # 页码不应该包含 '['
                    print(f"成功使用 {enc} 编码读取 {filename}")
                    return df
        except Exception:
            continue

    print(f"警告：无法完美解析 {filename}，将尝试强制读取，可能会有列错位。")
    # 最后尝试一次默认读取
    return pd.read_csv(filename, encoding='utf-8-sig', on_bad_lines='skip')


# ==========================================
# 4. 主程序
# ==========================================

def main():
    print("=== 开始读取文件 ===")
    df_std = read_csv_smart('bga_standard.csv')
    df_res = read_csv_smart('bga_result.csv')

    # --- 调试诊断：打印出Pandas读取到的数据样子，让你看清楚 ---
    print("\n[诊断] 提取结果(bga_result) 的前1行数据如下 (请检查'页码'列是否真的是数字):")
    if not df_res.empty:
        # 打印列名和第一行的对应关系
        first_row = df_res.iloc[0]
        print(f"{'列名':<25} | {'读取到的值'}")
        print("-" * 50)
        for col in df_res.columns[:5]:  # 只看前5列即可发现问题
            val = str(first_row[col])
            # 截断过长的显示
            if len(val) > 40: val = val[:37] + "..."
            print(f"{col:<25} | {val}")
    else:
        print("bga_result 为空！")
        return
    print("-" * 50)

    # --- 数据处理 ---
    print("\n正在清洗数据并匹配...")

    # 1. 转换页码 (带详细错误提示)
    df_std['clean_page'] = pd.to_numeric(df_std['页码'], errors='coerce')
    df_std = df_std.dropna(subset=['clean_page'])
    df_std['clean_page'] = df_std['clean_page'].astype(int)

    # 结果集页码转换
    df_res['clean_page_raw'] = df_res['页码']  # 备份一下
    df_res['clean_page'] = pd.to_numeric(df_res['页码'], errors='coerce')

    # 检查坏行
    bad_rows = df_res[df_res['clean_page'].isna()]
    if len(bad_rows) > 0:
        print(f"\n!!! 严重警告 !!!")
        print(f"bga_result.csv 中有 {len(bad_rows)} 行数据的'页码'无法识别为数字。")
        print(f"示例错误数据 (原值): {bad_rows.iloc[0]['clean_page_raw']}")
        print("这说明列错位了，请检查上面的[诊断]信息。")

    df_res = df_res.dropna(subset=['clean_page'])
    if df_res.empty:
        print("\n错误：清洗后没有剩余的有效行，程序终止。请检查CSV编码或格式。")
        return

    df_res['clean_page'] = df_res['clean_page'].astype(int)

    # 2. 生成 Key
    df_std['clean_name'] = df_std['PDF名称'].apply(normalize_filename)
    df_std['key'] = df_std['clean_name'] + "_" + df_std['clean_page'].astype(str)

    df_res['clean_name'] = df_res['PDF名称'].apply(normalize_filename)
    df_res['key'] = df_res['clean_name'] + "_" + df_res['clean_page'].astype(str)

    # 3. 去重
    df_std = df_std.drop_duplicates(subset=['key'])
    df_res = df_res.drop_duplicates(subset=['key'])

    # 4. 内容格式化
    for col in LIST_COLUMNS:
        if col in df_std.columns: df_std[col] = df_std[col].apply(parse_list_string)
        if col in df_res.columns: df_res[col] = df_res[col].apply(parse_list_string)  # 使用原始列名

    # Exclude Pins
    df_std['Exclude Pins'] = df_std['Exclude Pins'].apply(parse_exclude_pins)
    if 'Exclude Pins' in df_res.columns:
        df_res['Exclude Pins'] = df_res['Exclude Pins'].apply(parse_exclude_pins)

    # Package Type
    df_std['封装类型'] = df_std['封装类型'].apply(normalize_text)
    if 'package_type' in df_res.columns:
        df_res['package_type'] = df_res['package_type'].apply(normalize_text)

    # --- 对比 ---
    merged = pd.merge(df_std, df_res, on='key', how='left', suffixes=('_std', '_res'))

    total_rows = len(df_std)
    matched_rows = merged['PDF名称_res'].notna().sum()

    print(f"\n===== 对比结果 =====")
    print(f"标准集有效行数: {total_rows}")
    print(f"匹配到的行数:   {matched_rows}")
    print(f"文档匹配率:     {matched_rows / total_rows:.2%}")

    if matched_rows == 0:
        print("提示：匹配率为0通常意味着文件名(Key)对不上，或者数据根本没读进去。")
        return

    df_compare = merged[merged['PDF名称_res'].notna()].copy()

    # 准备对比的列
    cols_check = []
    for k, v in COLUMN_MAPPING.items():
        if k not in ['PDF名称', '页码']:
            cols_check.append((k, v))

    print(f"\n{'字段名':<30} | {'准确率':<10} | {'错误数':<10}")
    print("-" * 55)

    for std_col_name, res_col_name in cols_check:
        # 确定在merged dataframe中的实际列名
        # 如果result中列名和standard一样，merge后会带后缀
        key_std = std_col_name
        key_res = res_col_name

        if std_col_name in df_res.columns: key_std = std_col_name + '_std'
        if res_col_name in df_res.columns: key_res = res_col_name + '_res'

        # 检查列是否存在
        if key_res not in df_compare.columns:
            print(f"{std_col_name:<30} | {'N/A':<10} | (列缺失)")
            continue

        correct_count = 0
        for _, row in df_compare.iterrows():
            if compare_values(row.get(key_std), row.get(key_res), std_col_name):
                correct_count += 1

        acc = correct_count / matched_rows
        print(f"{std_col_name:<30} | {acc:.2%}    | {matched_rows - correct_count}")


if __name__ == '__main__':
    main()