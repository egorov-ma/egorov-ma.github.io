# Личный сайт

Статический сайт на Astro: главная, CV, проекты, заметки. Публикуется в GitHub Pages через GitHub Actions.

## Работа

```bash
npm install
npm run dev      # локально на http://localhost:4321
npm run build    # сборка в dist/
npm run verify   # проверка сборки: разделы CV, карточки проектов, утечки и трекеры
```

Проверка живого сайта: `bash scripts/verify-site.sh https://<домен>` (на адресе github.io — с флагом `--no-domain`).

## Контент

- CV — `src/pages/cv.astro`; исходные резюме в репозиторий не кладутся (запрет в `.gitignore`).
- Проекты — `src/data/projects.json`.
- Заметки — markdown в `src/pages/notes/`, поля `title`, `description`, `date`, опционально `source`.
