# F4 封装提取流程概要

本文件梳理 PackageExtract 模块中 F4 阶段（F4.1-F4.9）的主要函数与用法，便于快速定位处理逻辑。

## 总览
- **入口与职责**：`run_f4_pipeline` 串联检测、配对、OCR 与参数提取，输入为视图目录与封装类别，输出为整理好的参数列表（BGA/QFP 通用）。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L50-L137】
- **数据容器**：全流程共享的 `L3` 列表承载各视图的 YOLO/DBNet 结果、OCR 文本与配对中间态，所有步骤均通过 `common_pipeline` 的读写接口更新该结构。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L79-L119】

## 关键步骤
1. **数据汇总（F4.0）**：`common_pipeline.get_data_location_by_yolo_dbnet` 逐视图调用 YOLO+DBNet，缺失视图以空数组占位，构建初始 `L3`。
   【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L66-L84】【F:package_core/PackageExtract/common_pipeline.py†L168-L234】
2. **检测结果清洗（F4.1-F4.4）**：
   - `other_match_dbnet.other_match_boxes_by_overlap` 去除 OTHER 类干扰框；
   - `pin_match_dbnet.PINnum_find_matching_boxes`、`angle_match_dbnet.angle_find_matching_boxes`、`num_match_dbnet.num_match_size_boxes` 按 PIN/角度/数字信息修正尺寸线配对；
   - `num_direction.add_direction_field_to_yolox_nums` 为尺寸数字补充方向字段，便于后续匹配。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L85-L98】
3. **标尺补全与文本预处理（F4.6-F4.7）**：
   - `enrich_pairs_with_lines` 计算尺寸线端点距离并生成 `*_yolox_pairs_length`；
   - `preprocess_pairs_and_text` / `run_svtr_ocr` / `normalize_ocr_candidates` 依次准备副本、执行 OCR、统一最大/中值/最小候选，输出清洗后的 OCR 数据。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L98-L110】【F:package_core/PackageExtract/common_pipeline.py†L279-L400】
   - `match_triple_factor.match_arrow_pairs_with_yolox` 额外生成箭头-尺寸线三元组缓存，便于后续调试或补全。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L101-L105】
4. **序号提取与文本匹配（F4.8）**：
   - `extract_pin_serials` 在 QFP/QFN/SOP/SON 等封装下输出序号候选；
   - `match_pairs_with_text` 通过 MPD 算法重新配对尺寸线与 OCR，刷新四视图 OCR 列表。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L114-L116】【F:package_core/PackageExtract/common_pipeline.py†L403-L517】
5. **配对收敛与参数计算（F4.9）**：
   - `finalize_pairs` 综合尺寸线长度与副本，筛出稳定的尺寸线集合及对应 OCR 文本；
   - `compute_qfp_parameters` 计算 nx/ny、主体尺寸及各参数候选，最终由 `get_BGA_parameter_data` 转为输出列表。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L117-L137】【F:package_core/PackageExtract/common_pipeline.py†L577-L651】

## 标尺线匹配路径（F4.6-F4.9）
- **尺寸线补全**：`enrich_pairs_with_lines` 以尺寸线端点生成 `*_yolox_pairs_length`，后续作为配对和过滤的长度依据。【F:package_core/PackageExtract/common_pipeline.py†L318-L362】
- **文本-尺寸线再配对**：`match_pairs_with_text` 调用 `_pairs_module.MPD`，在已有 `matched_pairs_location` 基础上重算配对关系并返回刷新后的 OCR 数据。【F:package_core/PackageExtract/common_pipeline.py†L474-L516】
- **配对信息写回**：`get_pairs_info` 根据配对结果写入 outside/inside 标记，`get_yinxian_info` 补齐引线端点坐标，二者都以 `matched_pairs_location` 非空为前置条件。【F:package_core/PackageExtract/get_pairs_data_present5_test.py†L2424-L2446】
- **最终收敛**：`finalize_pairs` 调用 `get_better_data_2` 过滤掉缺少长度或副本支撑的配对，只保留稳定的 `yolox_pairs_*` 和同步后的 OCR 文本。【F:package_core/PackageExtract/common_pipeline.py†L519-L574】

### 可视化调试
- 需要逐视图核对标尺线匹配时，可调用 `_pairs_module.visualize_pairs_matching(img_path, pairs, test_mode=0, output_dir=None)`；
  该函数复用 `find_pairs_length` 的逻辑并在 ``output_dir``（默认 ``Result/Package_extract/opencv_output_yinXian/ruler_matching``）下保存：
  1) 直线检测结果；2) 每个尺寸线与最终引线的匹配叠加图。【F:package_core/PackageExtract/get_pairs_data_present5_test.py†L73-L160】【F:package_core/PackageExtract/get_pairs_data_present5_test.py†L188-L705】【F:package_core/PackageExtract/get_pairs_data_present5_test.py†L704-L708】

## Side 视图 A/A1 匹配策略（仅文档，待实现）
- **约束**：side 视图有效标注只会出现 A 与 A1 两项，A 通常是数值最大的框，A1 是比 A 小的那个；若检测框超过两个，最小值往往是噪声而非 A1。
- **建议逻辑**：
  1. 将 side 视图已配对到标尺线的 OCR 框按数值（`max_medium_min` 中的中值）降序排序；
  2. 取排序第 1 个作为 A，取剩余中数值最大的一个作为 A1（忽略最小值以规避噪声）；
  3. 若仅有 1 个有效框则暂记为 A，A1 置空并在日志中提示需要人工复核；
  4. 后续改动应在匹配或参数筛选阶段加入上述规则，而不影响未配对的其它视图。

## 使用提示
- `run_f4_pipeline` 会自动从目录收集视图文件名；若目录缺失则按默认 `top/bottom/side/detailed` 顺序尝试。
- `key` 影响 OCR 清洗与配对策略，`test_mode` 透传到尺寸线长度求解以辅助调试。
- 最终参数表已过 BGA/QFP 通用转换，可直接用于后续结构化存储或界面展示。【F:package_core/PackageExtract/BGA_Function/f4_pipeline_runner.py†L132-L137】
