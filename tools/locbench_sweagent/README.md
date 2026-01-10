# Loc-Bench SWE-agent 适配器

本目录包含三个脚本/配置，用于让 SWE-agent 在 Loc-Bench 上做“只定位、不修复”的实验，并把轨迹转换为评测需要的 `loc_outputs.jsonl` 格式。

## 使用前准备

- 安装 SWE-agent（已安装可跳过）：
  ```bash
  cd /Users/chz/code/locbench/SWE-agent
  pip install -e .
  ```
- 配置模型密钥（示例）：
  ```bash
  export OPENAI_API_KEY=...
  ```

## 使用方法

### 1) 生成 instances.jsonl

建议从仓库根目录（`locbench/`）执行：

```bash
python SWE-agent/tools/locbench_sweagent/prepare_instances.py \
  --dataset data/Loc-Bench_V1_dataset.jsonl \
  --repo-root locbench_repos \
  --output SWE-agent/tools/locbench_sweagent/instances_locbench.jsonl
```

可选参数：
- `--limit 10`：只生成前 10 条
- `--filter 'UXARRAY__uxarray-1117'`：只保留匹配的实例
- `--skip-missing`：跳过缺失镜像的实例

### 2) 本地运行 SWE-agent（定位模式）

```bash
cd SWE-agent
sweagent run-batch \
  --config config/locbench_localize.yaml \
  --agent.model.name <模型名> \
  --agent.model.per_instance_cost_limit <费用上限> \
  --instances.type file \
  --instances.path tools/locbench_sweagent/instances_locbench.jsonl \
  --instances.deployment.type local \
  --output_dir ../outputs/locbench_sweagent \
  --num_workers 1
```

如果本地部署参数报错，可查看需要的字段：
```bash
sweagent run-batch --help_option swerex.deployment.config.LocalDeploymentConfig
```

### 3) 轨迹转 loc_outputs.jsonl

```bash
python SWE-agent/tools/locbench_sweagent/parse_trajectories.py \
  --traj-dir outputs/locbench_sweagent \
  --dataset data/Loc-Bench_V1_dataset.jsonl \
  --output evaluation/loc_output/locagent/claude_3-5/loc_outputs.jsonl
```

## 风险与安全说明

- **数据集安全**：`data/Loc-Bench_V1_dataset.jsonl` 只会被读取，不会被修改。
- **仓库镜像风险**：本地运行会对 `locbench_repos/` 下的仓库执行
  `git reset --hard` 和 `git clean -fdq`，未提交修改和未跟踪文件会被清除。
  请确保 `locbench_repos/` 只是镜像，不存放你的工作内容。
- **输出位置**：所有生成结果只写到你指定的输出路径（如 `outputs/` 和 `evaluation/`），不会写回数据集。
- **定位输出解析**：`parse_trajectories.py` 会从每个 `.traj` 的最后 JSON 结果生成
  `found_files / found_modules / found_entities`；如果模型未输出 JSON，会提示 warning 并输出空列表。
