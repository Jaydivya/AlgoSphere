# compile_scss.py
import sass

css = sass.compile(filename='scss/bootstrap.scss', output_style='compressed')
with open('static/css/theme.css', 'w', encoding='utf-8') as f:
    f.write(css)
