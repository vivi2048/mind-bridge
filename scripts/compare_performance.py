#!/usr/bin/env python3
import csv

def parse_time(t):
    """解析时间字符串，如 '6.24s' -> 6.24"""
    return float(t.rstrip('s'))

def load_csv(filepath):
    """加载 CSV 文件"""
    rows = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['first_token_latency_sec'] = parse_time(row['first_token_latency'])
            row['total_time_sec'] = parse_time(row['total_time'])
            rows.append(row)
    return rows

# 读取两个版本
default_data = load_csv('tests/reports/test_report_20260721_093116.csv')
no_keyword_data = load_csv('tests/reports/test_report_no_keyword.csv')

# 找出异常值（响应时间 > 20s）
outliers_default = {r['id'] for r in default_data if r['total_time_sec'] > 20}
outliers_no_kw = {r['id'] for r in no_keyword_data if r['total_time_sec'] > 20}

print("=== Default 版本异常值（>20s）===")
for r in default_data:
    if r['total_time_sec'] > 20:
        print(f"  {r['id']}: {r['total_time_sec']:.1f}s")

print("\n=== No Keyword 版本异常值（>20s）===")
for r in no_keyword_data:
    if r['total_time_sec'] > 20:
        print(f"  {r['id']}: {r['total_time_sec']:.1f}s")

# 排除两个版本的异常值（取并集）
all_outliers = outliers_default | outliers_no_kw
print(f"\n共排除 {len(all_outliers)} 个异常值: {sorted(all_outliers)}")

# 排除异常值后计算
default_clean = [r for r in default_data if r['id'] not in all_outliers]
no_keyword_clean = [r for r in no_keyword_data if r['id'] not in all_outliers]

def calc_stats(data, field):
    values = [r[field] for r in data]
    n = len(values)
    avg = sum(values) / n
    sorted_vals = sorted(values)
    p50_idx = int(n * 0.5)
    p50 = sorted_vals[p50_idx]
    return avg, p50

print(f"\n=== 排除异常值后的对比（{len(default_clean)} 条）===")
print(f"{'指标':<20} {'No Keyword':<15} {'Default':<15} {'提升幅度':<10}")
print("-" * 60)

# 首字延迟
avg_first_no_kw, p50_first_no_kw = calc_stats(no_keyword_clean, 'first_token_latency_sec')
avg_first_def, p50_first_def = calc_stats(default_clean, 'first_token_latency_sec')
imp_first = (avg_first_no_kw - avg_first_def) / avg_first_no_kw * 100
imp_p50_first = (p50_first_no_kw - p50_first_def) / p50_first_no_kw * 100
print(f"{'首字延迟(平均)':<20} {avg_first_no_kw:<15.2f} {avg_first_def:<15.2f} {imp_first:>+6.1f}%")
print(f"{'首字延迟(P50)':<20} {p50_first_no_kw:<15.2f} {p50_first_def:<15.2f} {imp_p50_first:>+6.1f}%")

# 响应时间
avg_total_no_kw, p50_total_no_kw = calc_stats(no_keyword_clean, 'total_time_sec')
avg_total_def, p50_total_def = calc_stats(default_clean, 'total_time_sec')
imp_total = (avg_total_no_kw - avg_total_def) / avg_total_no_kw * 100
imp_p50_total = (p50_total_no_kw - p50_total_def) / p50_total_no_kw * 100
print(f"{'响应时间(平均)':<20} {avg_total_no_kw:<15.2f} {avg_total_def:<15.2f} {imp_total:>+6.1f}%")
print(f"{'响应时间(P50)':<20} {p50_total_no_kw:<15.2f} {p50_total_def:<15.2f} {imp_p50_total:>+6.1f}%")
