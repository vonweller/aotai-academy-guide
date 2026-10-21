# Blender · 鳌台书院三维场景

## 重跑
```bash
blender -b --factory-startup -P lib/build_academy.py     # 生成 out/aotai_academy.glb
blender -b --factory-startup -P lib/render_views.py      # 4 张 QC 渲染图 → qc/
```
生成后把 `out/aotai_academy.glb` 拷到 `03_网页3D/assets/`。

## 场景内容（单一合并网格，22 种材质，约 2.2 万面）
门楼牌坊「鰲台書院」+ 两扇开启门叶 + 一对石狮（含基座/鬃毛/绣球）·
两侧波浪云墙 + 圆形漏窗 · 前院青石板路/天井/水池/假山/竹丛/树 ·
主体讲堂（硬山顶灰瓦、白墙、廊柱、格栅门、匾额「講堂」、楹联）·
东侧非遗工坊 · 后园六角亭 · 地面草地。

## 匾额贴图
`05_Blender/tex/*.png` 由 `lib/make_plaque_tex.py`（宿主 Python + Pillow）生成；
Blender 平面 UV 的 U 轴反向，因此贴图生成时**预先水平镜像**，网页端加载后再做一次
`map.repeat.x = -1; map.offset.x = 1` 抵消；渲染 QC 图时脚本会自动翻回正向。
`lib/make_plaque_tex.py` 需在**宿主 Python**（有 Pillow）下跑，不在 Blender 内跑。

## 坐标约定
- Blender Z-up，米制，场景中心在原点，**门前朝 +Y**
- 导出 glTF→Y-up 后门前是 −Z，网页端对 GLB 做 `rotation.y = π` 归一到 +Z（与 map.json 一致）

## 导出
`export_format='GLB', export_yup=True, export_apply=True`，
合并后先 `transform_apply`，保证节点无位移；导出后 0.82 MB（含 4 张匾额/楹联贴图）。
