"""Z-Image Turbo text-to-image through the LOCAL ComfyUI (http://127.0.0.1:8188). No cloud nodes.

Reuses the HTTP client from tools/comfy_audio/comfy_client.py (_req/run), adds the image graph + fetch.
"""
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, '..', 'comfy_audio'))
import comfy_client as cc  # noqa: E402

cc.CLIENT = 'stickdoosh-art-' + cc.CLIENT.split('-')[-1]

UNET = 'z_image_turbo_bf16.safetensors'  # int8 variant: z_image_turbo_int8_convrot.safetensors
CLIP = 'qwen_3_4b.safetensors'
VAE = 'ae.safetensors'


def zimage_graph(prompt, w, h, seed, prefix, unet=UNET, steps=9):
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': unet, 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': CLIP, 'type': 'lumina2', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': VAE}},
        '4': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['1', 0], 'shift': 3.0}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['2', 0]}},
        '6': {'class_type': 'ConditioningZeroOut', 'inputs': {'conditioning': ['5', 0]}},
        '7': {'class_type': 'EmptySD3LatentImage', 'inputs': {'width': int(w), 'height': int(h), 'batch_size': 1}},
        '8': {'class_type': 'KSampler', 'inputs': {
            'model': ['4', 0], 'seed': int(seed), 'steps': int(steps), 'cfg': 1.0,
            'sampler_name': 'res_multistep', 'scheduler': 'simple',
            'positive': ['5', 0], 'negative': ['6', 0], 'latent_image': ['7', 0], 'denoise': 1.0}},
        '9': {'class_type': 'VAEDecode', 'inputs': {'samples': ['8', 0], 'vae': ['3', 0]}},
        '10': {'class_type': 'SaveImage', 'inputs': {'images': ['9', 0], 'filename_prefix': prefix}},
    }


def fetch_images(hist):
    out = []
    for _nid, o in (hist.get('outputs') or {}).items():
        for im in o.get('images', []) or []:
            q = urllib.parse.urlencode({'filename': im['filename'], 'subfolder': im.get('subfolder', ''),
                                        'type': im.get('type', 'output')})
            out.append((im['filename'], cc._req('/view?' + q, timeout=600)))
    return out


def generate(prompt, w, h, seed, prefix='stickdoosh/art/x', **kw):
    """Run one image, block until done. Returns (png_bytes, seconds)."""
    hist, dt = cc.run(zimage_graph(prompt, w, h, seed, prefix, **kw), timeout=3600)
    imgs = fetch_images(hist)
    if not imgs:
        raise RuntimeError('no image output')
    return imgs[0][1], dt
