# F4 封装提取流程概要

本文件梳理 PackageExtract 模块中 F4 阶段（F4.1-F4.9）的主要函数与用法，便于快速定位处理逻辑。

## 总览
- 入口：`f4_pipeline_runner.run_f4_pipeline` 串联了检测、配对、OCR 与参数提取的完整步骤，输入为包含视图图片的目录与封装类别，输出为参数列表。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L50-L137】
- 数据容器：各阶段共用的 `L3` 列表存放不同视图的 YOLO/DBNet 检测结果、OCR 文本及中间配对信息，由 `common_pipeline` 中的函数读写。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L79-L129】

## 关键步骤
1. **数据汇总（F4.0）**：`common_pipeline.get_data_location_by_yolo_dbnet` 按视图调用 YOLO/DBNet，生成 `L3` 初始内容，缺失视图则填充空数组，保持结构一致。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L79-L84】【F:package_core/PackageExtract/common_pipeline.py†L73-L136】
2. **检测结果清洗（F4.1-F4.4）**：
   - `other_match_dbnet.other_match_boxes_by_overlap` 剔除 OTHER 类框带来的干扰。
   - `pin_match_dbnet.PINnum_find_matching_boxes` 结合 PIN 和数字标注匹配尺寸线。
   - `angle_match_dbnet.angle_find_matching_boxes` 处理角度标注的配对。
   - `num_match_dbnet.num_match_size_boxes` 校正尺寸线与数字的对应关系。
   - `num_direction.add_direction_field_to_yolox_nums` 在尺寸数字中补充方向信息，供后续匹配使用。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L85-L98】
3. **标尺补全与文本预处理（F4.6-F4.7）**：
   - `common_pipeline.enrich_pairs_with_lines` 基于 OpenCV 结果补齐尺寸线端点，生成 `_yolox_pairs_length` 数据。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L98-L103】【F:package_core/PackageExtract/common_pipeline.py†L279-L314】
   - `common_pipeline.preprocess_pairs_and_text` 整理尺寸线/文本候选，并为 OCR 准备副本与缓存。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L103-L106】【F:package_core/PackageExtract/common_pipeline.py†L316-L366】
   - `common_pipeline.run_svtr_ocr` 与 `normalize_ocr_candidates` 执行 OCR 推理并归一化最大/中值/最小候选文本。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L106-L110】【F:package_core/PackageExtract/common_pipeline.py†L368-L456】
4. **序号提取与文本匹配（F4.8）**：
   - `common_pipeline.extract_pin_serials` 针对不同封装提取 PIN 序号信息（当前对 BGA 分支保留为注释）。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L114-L116】【F:package_core/PackageExtract/common_pipeline.py†L458-L511】
   - `common_pipeline.match_pairs_with_text` 调用 MPD 算法在尺寸线与 OCR 结果间重新配对，输出更新的 OCR 数据。【F:package_core/PackageExtract/common_pipeline.py†L478-L516】
5. **配对收敛与参数计算（F4.9）**：
   - `common_pipeline.finalize_pairs` 综合尺寸线长度、副本与 OCR 数据，过滤得到最终可用的配对集合。【F:package_core/PackageExtract/common_pipeline.py†L519-L574】
   - `common_pipeline.compute_qfp_parameters` 计算 nx/ny 与各参数候选列表，并调用 `function_tool.get_BGA_parameter_data` 生成输出参数列表。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L117-L137】【F:package_core/PackageExtract/common_pipeline.py†L577-L651】

## 使用提示
- `run_f4_pipeline` 支持自动从 `image_root` 读取可用视图文件；若目录缺失则按默认顺序尝试 `top/bottom/side/detailed`。
- `key` 参数会传递到 OCR 归一化与配对流程，用于控制数值清洗策略；`test_mode` 会影响尺寸线长度求解的调试输出。
- 输出的参数列表已过 BGA/QFP 通用转换，便于后续结构化存储或界面展示。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L132-L137】
