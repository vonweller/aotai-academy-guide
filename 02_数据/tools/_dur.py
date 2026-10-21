import os, struct, wave
ROOT = os.path.join('02_数据','audio')
def dur(path):
    # 用 ffprobe 拿精确时长
    import subprocess
    try:
        out = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                              '-of','default=nw=1:nk=1', path], capture_output=True, text=True, timeout=20)
        return float(out.stdout.strip())
    except Exception as e:
        return -1
for lang in ('zh','yue'):
    for name in ('s1_welcome_ok','s1_welcome_new','s1_prompt'):
        p = os.path.join(ROOT, lang, name + '.mp3')
        if os.path.exists(p):
            print(lang, name, round(dur(p), 2), 's')