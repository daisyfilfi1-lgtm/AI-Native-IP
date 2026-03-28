"""
AutoTune - 参数自动优化框架

基于 Karpathy 的 AutoResearch 思想：
- 固定时间预算
- 客观可测指标
- 自动改参数/跑实验/评估/保留或回滚

适用场景：
- 知识库录入参数优化 (chunk_size, overlap, batch_size)
- 检索参数优化 (top_k, weights)
- 内容生成参数优化 (temperature, max_tokens)

使用:
    python scripts/autotune.py --target ingest --metric recall
    python scripts/autotune.py --target retrieve --metric latency
"""
import os
import sys
import json
import time
import random
import argparse
import subprocess
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加项目根目录
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.env_loader import load_backend_env
load_backend_env()

# ============================================================
# 配置空间 - 在这里定义要优化的参数
# ============================================================

# 知识库录入参数空间
INGEST_PARAM_SPACE = {
    "CHUNK_SIZE": [500, 800, 1000, 1500, 2000],
    "CHUNK_OVERLAP": [50, 100, 150, 200],
    "INGEST_EMBED_BATCH_SIZE": [4, 8, 16, 32],
    "INGEST_COMMIT_EVERY": [10, 20, 30, 50],
}

# 检索参数空间
RETRIEVE_PARAM_SPACE = {
    "TOP_K": [3, 5, 10, 15, 20],
    "VECTOR_WEIGHT": [0.3, 0.5, 0.7, 0.8],
    "HYBRID_MIN_SCORE": [0.1, 0.2, 0.3, 0.5],
}

# 内容生成参数空间
GENERATION_PARAM_SPACE = {
    "TEMPERATURE": [0.1, 0.3, 0.5, 0.7, 0.9],
    "MAX_TOKENS": [500, 1000, 1500, 2000],
    "TOP_P": [0.8, 0.9, 0.95, 1.0],
}


@dataclass
class Experiment:
    """单次实验记录"""
    id: str
    timestamp: str
    target: str  # ingest/retrieve/generation
    params: Dict[str, Any]
    metric: str   # recall/latency/quality
    score: float
    duration: float  # 秒
    status: str  # success/failed
    error: Optional[str] = None


class AutoTuner:
    """自动参数优化器"""
    
    def __init__(
        self,
        target: str = "ingest",
        metric: str = "recall",
        time_budget: int = 300,  # 5分钟
        experiments_dir: str = None,
    ):
        self.target = target
        self.metric = metric
        self.time_budget = time_budget
        self.experiments: List[Experiment] = []
        
        # 设置参数空间
        self.param_space = self._get_param_space(target)
        
        # 实验目录
        self.experiments_dir = Path(experiments_dir or backend_dir / "data" / "autotune")
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前最佳参数
        self.best_params = None
        self.best_score = float('-inf') if metric != "latency" else float('inf')
        
        # 加载历史最佳
        self._load_best()
    
    def _get_param_space(self, target: str) -> Dict[str, List]:
        """获取参数空间"""
        spaces = {
            "ingest": INGEST_PARAM_SPACE,
            "retrieve": RETRIEVE_PARAM_SPACE,
            "generation": GENERATION_PARAM_SPACE,
        }
        return spaces.get(target, INGEST_PARAM_SPACE)
    
    def _generate_params(self) -> Dict[str, Any]:
        """随机生成一组参数"""
        params = {}
        for param_name, values in self.param_space.items():
            params[param_name] = random.choice(values)
        return params
    
    def _apply_params(self, params: Dict[str, Any]) -> bool:
        """应用参数到环境变量"""
        try:
            for key, value in params.items():
                os.environ[key] = str(value)
            return True
        except Exception as e:
            print(f"应用参数失败: {e}")
            return False
    
    def _run_experiment(self, params: Dict[str, Any]) -> Experiment:
        """运行单次实验"""
        exp_id = f"exp_{len(self.experiments):04d}_{int(time.time())}"
        timestamp = datetime.now().isoformat()
        
        start_time = time.time()
        
        try:
            # 应用参数
            if not self._apply_params(params):
                raise Exception("参数应用失败")
            
            # 运行目标实验
            score = self._evaluate(params)
            
            duration = time.time() - start_time
            
            experiment = Experiment(
                id=exp_id,
                timestamp=timestamp,
                target=self.target,
                params=params,
                metric=self.metric,
                score=score,
                duration=duration,
                status="success",
            )
            
        except Exception as e:
            duration = time.time() - start_time
            experiment = Experiment(
                id=exp_id,
                timestamp=timestamp,
                target=self.target,
                params=params,
                metric=self.metric,
                score=float('-inf') if self.metric != "latency" else float('inf'),
                duration=duration,
                status="failed",
                error=str(e),
            )
        
        return experiment
    
    def _evaluate(self, params: Dict[str, Any]) -> float:
        """评估参数效果"""
        # 这里应该调用实际的评估函数
        # 根据 target 和 metric 选择评估方式
        
        if self.target == "ingest":
            return self._evaluate_ingest(params)
        elif self.target == "retrieve":
            return self._evaluate_retrieve(params)
        else:
            return self._evaluate_generation(params)
    
    def _evaluate_ingest(self, params: Dict[str, Any]) -> float:
        """评估知识库录入效果"""
        # 实际实现：运行一个小规模录入，测量：
        # - 吞吐量 (chunks/second)
        # - 内存使用
        # - 成功率
        
        # 模拟评估（实际需要接入真实测试）
        chunk_size = params.get("CHUNK_SIZE", 1000)
        batch_size = params.get("INGEST_EMBED_BATCH_SIZE", 8)
        
        # 模拟评分逻辑：平衡吞吐量和质量
        throughput_score = (chunk_size / 1000) * (batch_size / 8)
        quality_score = 1.0 - (chunk_size / 3000)  # 越小质量越高
        
        # 综合得分（越大越好）
        score = throughput_score * 0.3 + quality_score * 0.7
        
        return score
    
    def _evaluate_retrieve(self, params: Dict[str, Any]) -> float:
        """评估检索效果"""
        top_k = params.get("TOP_K", 10)
        vector_weight = params.get("VECTOR_WEIGHT", 0.5)
        
        # 模拟评分
        recall_proxy = min(1.0, top_k / 15)  # 更大的top_k通常意味着更高的recall
        balance_proxy = 1.0 - abs(vector_weight - 0.5) * 0.5  # 平衡的权重通常更好
        
        return recall_proxy * 0.7 + balance_proxy * 0.3
    
    def _evaluate_generation(self, params: Dict[str, Any]) -> float:
        """评估生成效果"""
        temp = params.get("TEMPERATURE", 0.5)
        
        # 模拟评分
        if self.metric == "quality":
            # 中等温度通常质量较好
            score = 1.0 - abs(temp - 0.5) * 0.5
        else:
            # 延迟：更大的max_tokens意味着更慢
            max_tokens = params.get("MAX_TOKENS", 1000)
            score = 2000 / max_tokens  # 越小越快
        
        return score
    
    def _load_best(self):
        """加载历史最佳参数"""
        best_file = self.experiments_dir / "best_params.json"
        if best_file.exists():
            with open(best_file, 'r') as f:
                data = json.load(f)
                self.best_params = data.get(self.target, {})
                self.best_score = data.get(f"{self.target}_score", float('-inf'))
    
    def _save_best(self):
        """保存最佳参数"""
        best_file = self.experiments_dir / "best_params.json"
        
        data = {}
        if best_file.exists():
            with open(best_file, 'r') as f:
                data = json.load(f)
        
        data[self.target] = self.best_params
        data[f"{self.target}_score"] = self.best_score
        
        with open(best_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_experiment(self, experiment: Experiment):
        """保存实验结果"""
        exp_file = self.experiments_dir / f"{experiment.id}.json"
        with open(exp_file, 'w') as f:
            json.dump(asdict(experiment), f, indent=2, ensure_ascii=False)
    
    def run(self, max_experiments: int = None):
        """运行自动优化"""
        print(f"\n{'='*60}")
        print(f"AutoTune - {self.target} optimization")
        print(f"Target metric: {self.metric}")
        print(f"Time budget: {self.time_budget}s")
        print(f"Param space: {list(self.param_space.keys())}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        experiment_count = 0
        
        while True:
            # 检查时间预算
            elapsed = time.time() - start_time
            if elapsed >= self.time_budget:
                print(f"\nTime budget exhausted, stopping")
                break
            
            # 检查实验次数
            if max_experiments and experiment_count >= max_experiments:
                print(f"\nMax experiments reached, stopping")
                break
            
            # 生成参数（可以加入一些随机扰动来探索）
            params = self._generate_params()
            
            print(f"[{experiment_count + 1}] Testing params: {params}")
            
            # 运行实验
            experiment = self._run_experiment(params)
            self.experiments.append(experiment)
            
            # 打印结果
            if experiment.status == "success":
                print(f"    Score: {experiment.score:.4f} ({experiment.duration:.1f}s)")
                
                # 判断是否更好
                is_better = (
                    self.metric == "latency" 
                    if experiment.score < self.best_score 
                    else experiment.score > self.best_score
                )
                
                if is_better:
                    print(f"    NEW BEST!")
                    self.best_params = params.copy()
                    self.best_score = experiment.score
                    self._save_best()
            else:
                print(f"    FAILED: {experiment.error}")
            
            # 保存实验记录
            self._save_experiment(experiment)
            
            experiment_count += 1
            
            # 每10个实验输出摘要
            if experiment_count % 10 == 0:
                self._print_summary()
        
        # 最终总结
        self._print_final_summary()
        
        return self.best_params
    
    def _print_summary(self):
        """打印实验摘要"""
        successful = [e for e in self.experiments if e.status == "success"]
        if not successful:
            return
        
        scores = [e.score for e in successful]
        avg_score = sum(scores) / len(scores)
        
        print(f"\n--- Summary ({len(successful)}/{len(self.experiments)} success) ---")
        print(f"Avg score: {avg_score:.4f}")
        print(f"Current best: {self.best_score:.4f}")
        print(f"Best params: {self.best_params}")
    
    def _print_final_summary(self):
        """打印最终总结"""
        print(f"\n{'='*60}")
        print(f"Optimization Complete!")
        print(f"Total experiments: {len(self.experiments)}")
        print(f"Successful: {len([e for e in self.experiments if e.status == 'success'])}")
        print(f"Best score: {self.best_score:.4f}")
        print(f"Best params: {json.dumps(self.best_params, indent=2, ensure_ascii=False)}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="AutoTune - 参数自动优化")
    parser.add_argument("--target", "-t", default="ingest", 
                       choices=["ingest", "retrieve", "generation"],
                       help="优化目标")
    parser.add_argument("--metric", "-m", default="recall",
                       help="评估指标 (recall/latency/quality)")
    parser.add_argument("--time", default=300, type=int,
                       help="时间预算（秒）")
    parser.add_argument("--max", "-n", type=int, default=None,
                       help="最大实验次数")
    parser.add_argument("--seed", type=int, default=42,
                       help="随机种子")
    
    args = parser.parse_args()
    
    # 设置随机种子
    random.seed(args.seed)
    
    # 确保输出编码为UTF-8
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # 创建优化器并运行
    tuner = AutoTuner(
        target=args.target,
        metric=args.metric,
        time_budget=args.time,
    )
    
    best_params = tuner.run(max_experiments=args.max)
    
    # 输出推荐参数
    print("\nRecommended params:")
    for key, value in best_params.items():
        print(f"  {key}={value}")


if __name__ == "__main__":
    main()
