"""
Generate compare_images.html — side-by-side comparison of Wikimedia vs
manufacturer images for each make/model so the owners can evaluate quality
and coverage before we commit to one source.

Run after fetch_images_wikimedia.py and fetch_images_manufacturer.py.
Output: compare_images.html (open in browser, no server needed).
"""
import json
from pathlib import Path
from typing import List, Dict

from scripts.config import IMAGES_DIR, TARGET_MODELS, MODEL_YEARS
from scripts.utils import get_logger

logger = get_logger(__name__)

OUTPUT_PATH = Path(__file__).parent.parent / "compare_images.html"


def load_manifest() -> dict:
    path = IMAGES_DIR / "manifest.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def group_by_model(entries: List[dict]) -> Dict[str, List[dict]]:
    """Group manifest entries by 'make/model' key."""
    grouped = {}
    for entry in entries:
        key = f"{entry.get('make', '')} {entry.get('model', '')}"
        grouped.setdefault(key, []).append(entry)
    return grouped


def image_tag(local_path: str, source: str) -> str:
    """Return an <img> tag with a relative path from the project root."""
    full = IMAGES_DIR / local_path
    rel = full  # already a Path
    # Use the path relative to the HTML file location (project root)
    return f'<img src="{rel}" alt="{source} image" loading="lazy" onerror="this.style.display=\'none\'">'


def render_model_section(model_key: str, wiki_imgs: List[dict], mfr_imgs: List[dict]) -> str:
    make, model = model_key.split(" ", 1)

    def imgs_html(imgs, source_label):
        if not imgs:
            return f'<div class="empty">No {source_label} images found</div>'
        tags = "\n".join(image_tag(img["local_path"], source_label) for img in imgs)
        attribution = imgs[0].get("attribution", "") if source_label == "Wikimedia" else ""
        attr_html = f'<p class="attribution">Credit: {attribution}</p>' if attribution else ""
        return f'<div class="img-grid">{tags}</div>{attr_html}'

    wiki_html = imgs_html(wiki_imgs, "Wikimedia")
    mfr_html = imgs_html(mfr_imgs, "Manufacturer")

    return f"""
    <section class="model-section">
      <h2>{model_key}</h2>
      <div class="compare-row">
        <div class="source-col">
          <h3>Wikimedia Commons <span class="badge badge-wiki">Free / CC Licensed</span></h3>
          <p class="count">{len(wiki_imgs)} image(s)</p>
          {wiki_html}
        </div>
        <div class="source-col">
          <h3>Manufacturer Site <span class="badge badge-mfr">Official Press Photos</span></h3>
          <p class="count">{len(mfr_imgs)} image(s)</p>
          {mfr_html}
        </div>
      </div>
    </section>
    """


def render_html(sections: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Image Source Comparison — Car Vision Board</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #f5f5f5; color: #222; padding: 24px; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 8px; }}
    .subtitle {{ color: #555; margin-bottom: 32px; font-size: 0.95rem; }}
    .model-section {{ background: white; border-radius: 8px; padding: 24px;
                     margin-bottom: 32px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    h2 {{ font-size: 1.4rem; margin-bottom: 16px; border-bottom: 2px solid #eee;
          padding-bottom: 8px; }}
    .compare-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    @media (max-width: 800px) {{ .compare-row {{ grid-template-columns: 1fr; }} }}
    .source-col h3 {{ font-size: 1rem; margin-bottom: 4px; display: flex;
                      align-items: center; gap: 8px; }}
    .badge {{ font-size: 0.7rem; font-weight: 600; padding: 2px 8px;
              border-radius: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .badge-wiki {{ background: #e8f5e9; color: #2e7d32; }}
    .badge-mfr  {{ background: #e3f2fd; color: #1565c0; }}
    .count {{ color: #888; font-size: 0.85rem; margin-bottom: 12px; }}
    .img-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                 gap: 8px; }}
    .img-grid img {{ width: 100%; height: 140px; object-fit: cover; border-radius: 4px;
                     border: 1px solid #ddd; cursor: pointer; transition: opacity 0.2s; }}
    .img-grid img:hover {{ opacity: 0.85; }}
    .empty {{ color: #999; font-style: italic; padding: 16px 0; }}
    .attribution {{ font-size: 0.75rem; color: #888; margin-top: 6px; }}
    /* Lightbox */
    #lightbox {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85);
                 z-index: 1000; align-items: center; justify-content: center; }}
    #lightbox.open {{ display: flex; }}
    #lightbox img {{ max-width: 90vw; max-height: 90vh; border-radius: 4px; }}
    #lightbox-close {{ position: fixed; top: 16px; right: 24px; font-size: 2rem;
                       color: white; cursor: pointer; background: none; border: none; }}
    .toc {{ background: white; border-radius: 8px; padding: 16px 24px; margin-bottom: 24px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    .toc h2 {{ font-size: 1rem; margin-bottom: 8px; }}
    .toc ul {{ list-style: none; columns: 2; }}
    .toc a {{ color: #1565c0; text-decoration: none; font-size: 0.9rem; }}
    .toc a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Image Source Comparison</h1>
  <p class="subtitle">
    Compare Wikimedia Commons vs manufacturer website images for each model.
    Click any image to enlarge. Use this page to decide which source to use.
  </p>

  <div id="lightbox">
    <button id="lightbox-close" onclick="closeLightbox()">&#x2715;</button>
    <img id="lightbox-img" src="" alt="">
  </div>

  {sections}

  <script>
    document.querySelectorAll('.img-grid img').forEach(img => {{
      img.addEventListener('click', () => {{
        document.getElementById('lightbox-img').src = img.src;
        document.getElementById('lightbox').classList.add('open');
      }});
    }});
    function closeLightbox() {{
      document.getElementById('lightbox').classList.remove('open');
    }}
    document.getElementById('lightbox').addEventListener('click', e => {{
      if (e.target.id === 'lightbox') closeLightbox();
    }});
    document.addEventListener('keydown', e => {{
      if (e.key === 'Escape') closeLightbox();
    }});
  </script>
</body>
</html>"""


def run():
    manifest = load_manifest()
    wiki_entries = manifest.get("wikimedia", [])
    mfr_entries = manifest.get("manufacturer", [])

    wiki_by_model = group_by_model(wiki_entries)
    mfr_by_model = group_by_model(mfr_entries)

    all_models = sorted(set(list(wiki_by_model.keys()) + list(mfr_by_model.keys())))

    if not all_models:
        # If no images have been downloaded yet, generate a placeholder page
        logger.warning(
            "No images found in manifest. Run fetch_images_wikimedia.py and "
            "fetch_images_manufacturer.py first."
        )
        placeholder = "<p style='padding:40px;color:#888'>No images downloaded yet. Run the fetch scripts first.</p>"
        OUTPUT_PATH.write_text(render_html(placeholder))
        logger.info("Wrote placeholder: %s", OUTPUT_PATH)
        return

    sections = "\n".join(
        render_model_section(
            model_key,
            wiki_by_model.get(model_key, []),
            mfr_by_model.get(model_key, []),
        )
        for model_key in all_models
    )

    OUTPUT_PATH.write_text(render_html(sections))
    logger.info("Generated: %s", OUTPUT_PATH)
    logger.info("Open compare_images.html in your browser to evaluate image sources.")


if __name__ == "__main__":
    run()
