"""
MindBridge 高并发压测脚本
功能: 模拟多用户并发聊天请求, 测量系统在高压下的可用性和性能
指标: 首字延迟、响应时间、吞吐量(RPS)、错误率、超时率
"""

import asyncio
import argparse
import json
import time
import csv
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import httpx
from tqdm import tqdm

from app.core.config import settings
from app.core.logging_config import setup_logging

setup_logging(console_output=False)
logger = logging.getLogger(__name__)

# 压测用测试问题集 (覆盖不同场景)
TEST_QUESTIONS = [
    "你好",
    "最近心情不太好,有什么建议吗?",
    "我最近压力很大,晚上总是失眠",
    "考试焦虑怎么办?",
    "如何提高注意力?",
    "和朋友吵架了,心里很难受",
    "我觉得自己什么都做不好",
    "拖延症怎么改善?",
    "最近总是感到疲惫,提不起精神",
    "社交场合总是很紧张,怎么办?",
    "和父母关系不太好,很压抑",
    "如何调节情绪?",
    "总是担心未来,很焦虑",
    "感觉自己很孤独,没有朋友",
    "睡眠质量很差,有什么方法改善?",
    "如何建立自信?",
    "最近总是烦躁不安",
    "怎样缓解学习压力?",
    "总是和别人比较,心里不平衡",
    "如何保持积极的心态?",
]


class LoadTester:
    """高并发压测器"""

    def __init__(self, api_url: str = "http://localhost:8000/api/chat"):
        self.api_url = api_url
        self.test_user_id = 1001
        self.session_counter = 0
        self.results: List[Dict] = []
        self._csv_lock = asyncio.Lock()

    def get_unique_session_id(self) -> int:
        """生成唯一的 session_id (900000+ 范围)"""
        self.session_counter += 1
        return 900000 + self.session_counter

    async def send_streaming_request(
        self, question: str, session_id: int, max_retries: int = 1
    ) -> Dict:
        """发送 SSE 流式请求并收集性能指标"""
        start_time = time.time()
        first_token_time = None
        full_response = ""
        token_count = 0

        timeout_config = httpx.Timeout(120.0, connect=15.0)

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    async with client.stream(
                        "POST",
                        self.api_url,
                        json={
                            "user_id": self.test_user_id,
                            "session_id": session_id,
                            "message": question,
                        },
                    ) as response:
                        if response.status_code != 200:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status_code}",
                                "first_token_latency": 0,
                                "total_time": time.time() - start_time,
                                "token_count": 0,
                            }

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                try:
                                    data = json.loads(data_str)

                                    if data.get("type") == "token":
                                        if first_token_time is None:
                                            first_token_time = time.time()
                                        full_response += data.get("content", "")
                                        token_count += 1

                                    elif data.get("type") == "done":
                                        break

                                    elif data.get("type") == "error":
                                        return {
                                            "success": False,
                                            "error": data.get("message", "Unknown"),
                                            "first_token_latency": 0,
                                            "total_time": time.time() - start_time,
                                            "token_count": 0,
                                        }

                                except json.JSONDecodeError:
                                    continue

                break  # 成功完成, 跳出重试循环

            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                if attempt < max_retries:
                    await asyncio.sleep(1)
                else:
                    return {
                        "success": False,
                        "error": f"超时(重试{max_retries}次)",
                        "first_token_latency": 0,
                        "total_time": time.time() - start_time,
                        "token_count": 0,
                    }
            except httpx.ConnectError as e:
                return {
                    "success": False,
                    "error": f"连接失败: {e}",
                    "first_token_latency": 0,
                    "total_time": time.time() - start_time,
                    "token_count": 0,
                }
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(1)
                else:
                    return {
                        "success": False,
                        "error": str(e)[:100],
                        "first_token_latency": 0,
                        "total_time": time.time() - start_time,
                        "token_count": 0,
                    }

        end_time = time.time()

        return {
            "success": True,
            "first_token_latency": (first_token_time - start_time)
            if first_token_time
            else 0,
            "total_time": end_time - start_time,
            "token_count": token_count,
        }

    async def run_worker(
        self,
        semaphore: asyncio.Semaphore,
        worker_id: int,
        duration: float,
        pbar: tqdm,
        level_results: List[Dict],
    ):
        """单个虚拟用户工作线程: 在指定时间内持续发送请求"""
        async with semaphore:
            end_deadline = time.time() + duration

            while time.time() < end_deadline:
                question = random.choice(TEST_QUESTIONS)
                session_id = self.get_unique_session_id()

                result = await self.send_streaming_request(question, session_id)
                result["worker_id"] = worker_id
                result["question"] = question[:30]

                level_results.append(result)
                pbar.update(1)

                if not result["success"]:
                    pbar.set_postfix(err=level_results.count(None) if False else sum(
                        1 for r in level_results if not r.get("success")
                    ))

                # 短暂间隔, 模拟真实用户节奏 (0.5-2s)
                await asyncio.sleep(random.uniform(0.5, 2.0))

    def _calculate_percentiles(self, data: list) -> Dict[str, float]:
        """计算百分位数"""
        if not data:
            return {"P50": 0, "P90": 0, "P95": 0, "P99": 0}

        sorted_data = sorted(data)
        n = len(sorted_data)

        def percentile(p):
            k = (n - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < n else f
            d = k - f
            return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])

        return {
            "P50": percentile(50),
            "P90": percentile(90),
            "P95": percentile(95),
            "P99": percentile(99),
        }

    async def run_level(self, concurrency: int, duration: float) -> List[Dict]:
        """运行单个并发级别的压测"""
        level_results: List[Dict] = []
        semaphore = asyncio.Semaphore(concurrency)

        pbar = tqdm(
            total=None,  # 无限进度条 (按时间控制)
            desc=f"  并发 {concurrency}",
            unit="req",
            bar_format="{l_bar}{bar}| {n_fmt} [{elapsed}<{remaining}]",
        )

        # 启动所有虚拟用户工作线程
        workers = [
            self.run_worker(semaphore, i, duration, pbar, level_results)
            for i in range(concurrency)
        ]

        await asyncio.gather(*workers)
        pbar.close()

        return level_results

    def print_level_summary(self, concurrency: int, results: List[Dict], duration: float):
        """打印单个级别的统计摘要"""
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        failed = total - success
        rps = total / duration

        print(f"\n  {'─' * 50}")
        print(f"  并发: {concurrency} | 请求: {total} | 成功: {success} | 失败: {failed} | RPS: {rps:.1f}")

        if failed > 0:
            error_types = {}
            for r in results:
                if not r.get("success"):
                    err = r.get("error", "unknown")[:30]
                    error_types[err] = error_types.get(err, 0) + 1
            for err, count in sorted(error_types.items(), key=lambda x: -x[1]):
                print(f"    ✗ {err}: {count}次")

        # 性能统计 (仅成功请求)
        success_results = [r for r in results if r.get("success")]
        if success_results:
            first_tokens = [r["first_token_latency"] for r in success_results if r["first_token_latency"] > 0]
            total_times = [r["total_time"] for r in success_results]

            if first_tokens:
                ft_pct = self._calculate_percentiles(first_tokens)
                print(f"    首字延迟: 平均{sum(first_tokens)/len(first_tokens):.2f}s | P50:{ft_pct['P50']:.2f}s | P90:{ft_pct['P90']:.2f}s | P95:{ft_pct['P95']:.2f}s")

            if total_times:
                tt_pct = self._calculate_percentiles(total_times)
                print(f"    响应时间: 平均{sum(total_times)/len(total_times):.2f}s | P50:{tt_pct['P50']:.2f}s | P90:{tt_pct['P90']:.2f}s | P95:{tt_pct['P95']:.2f}s")

            tokens = [r["token_count"] for r in success_results]
            if tokens:
                print(f"    Token: 平均{sum(tokens)/len(tokens):.0f}/请求 | 总{sum(tokens)}")

    async def clean_test_data(self):
        """清理数据库中的测试数据"""
        if not settings.database_url:
            print("DATABASE_URL 未配置,跳过数据清理")
            return

        from sqlalchemy import select, delete
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from app.models.entities import ChatSession, ChatMessage, RiskEvent

        try:
            engine = create_async_engine(settings.database_url, echo=False)
        except Exception as e:
            print(f"数据库连接失败,跳过清理: {e}")
            return

        try:
            async with AsyncSession(engine) as session:
                # 清理测试消息
                msg_result = await session.execute(
                    select(ChatMessage).where(ChatMessage.session_id >= 900000)
                )
                msg_count = len(msg_result.scalars().all())
                await session.execute(
                    delete(ChatMessage).where(ChatMessage.session_id >= 900000)
                )

                # 清理测试会话
                await session.execute(
                    delete(ChatSession).where(ChatSession.id >= 900000)
                )

                # 清理测试风险事件
                await session.execute(
                    delete(RiskEvent).where(RiskEvent.session_id >= 900000)
                )

                await session.commit()
                logger.info(f"已清理测试数据: 消息{msg_count}条")
        except Exception as e:
            logger.error(f"清理测试数据失败: {e}")
        finally:
            await engine.dispose()

    def save_results(self, output_path: str):
        """保存详细结果到 CSV"""
        if not self.results:
            return

        fieldnames = [
            "level", "worker_id", "question", "success", "error",
            "first_token_latency", "total_time", "token_count",
        ]

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.results:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

        print(f"\n✓ 详细结果已保存: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="MindBridge 高并发压测")
    parser.add_argument("--concurrent", type=int, default=0,
                        help="固定并发数 (0=梯度压测)")
    parser.add_argument("--duration", type=float, default=30,
                        help="每个级别的持续时间(秒)")
    parser.add_argument("--levels", type=str, default="5,10,20,30,50",
                        help="梯度并发级别(逗号分隔)")
    args = parser.parse_args()

    print("=" * 60)
    print("MindBridge 高并发压测")
    print("=" * 60)

    tester = LoadTester()

    # 确定压测级别
    if args.concurrent > 0:
        levels = [args.concurrent]
        print(f"\n模式: 固定并发 {args.concurrent}, 持续 {args.duration}s")
    else:
        levels = [int(x) for x in args.levels.split(",")]
        print(f"\n模式: 梯度压测 {levels}, 每级持续 {args.duration}s")

    print(f"问题池: {len(TEST_QUESTIONS)} 条")
    print(f"API: {tester.api_url}")

    # 先清理历史测试数据
    print("\n清理历史测试数据...")
    await tester.clean_test_data()

    # 逐级执行压测
    all_level_summaries = []

    for level in levels:
        print(f"\n{'━' * 60}")
        print(f"开始压测: 并发 {level}, 持续 {args.duration}s")
        print(f"{'━' * 60}")

        level_start = time.time()
        level_results = await tester.run_level(level, args.duration)
        level_duration = time.time() - level_start

        # 为结果添加级别标记
        for r in level_results:
            r["level"] = level

        tester.results.extend(level_results)
        tester.print_level_summary(level, level_results, level_duration)

        # 收集摘要数据
        total = len(level_results)
        success = sum(1 for r in level_results if r.get("success"))
        all_level_summaries.append({
            "concurrency": level,
            "total": total,
            "success": success,
            "failed": total - success,
            "rps": total / level_duration,
            "duration": level_duration,
        })

    # 最终汇总
    print(f"\n{'=' * 60}")
    print("压测汇总")
    print(f"{'=' * 60}")
    print(f"\n{'并发':>6} | {'请求':>6} | {'成功':>6} | {'失败':>6} | {'成功率':>8} | {'RPS':>8}")
    print("─" * 55)

    for s in all_level_summaries:
        rate = s["success"] / s["total"] * 100 if s["total"] > 0 else 0
        print(f"{s['concurrency']:>6} | {s['total']:>6} | {s['success']:>6} | {s['failed']:>6} | {rate:>7.1f}% | {s['rps']:>7.1f}")

    total_requests = sum(s["total"] for s in all_level_summaries)
    total_success = sum(s["success"] for s in all_level_summaries)
    total_failed = sum(s["failed"] for s in all_level_summaries)

    print("─" * 55)
    overall_rate = total_success / total_requests * 100 if total_requests > 0 else 0
    print(f"{'合计':>6} | {total_requests:>6} | {total_success:>6} | {total_failed:>6} | {overall_rate:>7.1f}% |")

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"tests/reports/load_test_{timestamp}.csv"
    Path("tests/reports").mkdir(exist_ok=True)
    tester.save_results(csv_path)

    # 保存汇总
    summary_path = f"tests/reports/load_test_{timestamp}_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"MindBridge 高并发压测报告\n")
        f.write(f"时间: {timestamp}\n")
        f.write(f"{'=' * 50}\n\n")
        for s in all_level_summaries:
            f.write(f"并发 {s['concurrency']}: {s['total']}请求, "
                    f"成功{s['success']}, 失败{s['failed']}, "
                    f"RPS:{s['rps']:.1f}\n")
        f.write(f"\n总计: {total_requests}请求, 成功率{overall_rate:.1f}%\n")
    print(f"✓ 汇总报告已保存: {summary_path}")

    # 清理测试数据
    print("\n清理测试数据...")
    await tester.clean_test_data()
    print("清理完成")


if __name__ == "__main__":
    asyncio.run(main())
