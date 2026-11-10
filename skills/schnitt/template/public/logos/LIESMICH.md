# Logos

Leg hier die echten Logos der Apps und Marken ab, über die du im Video sprichst
(PNG oder SVG, quadratisch, mindestens 512 px). Grafiken und das Plakat holen
sie mit `staticFile('logos/<datei>')`.

Auf dem Mac liegt das Icon einer App in ihrem Programmpaket:

```bash
sips -s format png -z 1024 1024 /Applications/<App>.app/Contents/Resources/<Icon>.icns --out public/logos/<app>.png
```

Nimm nur Logos, die du zeigen darfst. Ein nachgebautes Text-Icon ist kein Ersatz.
