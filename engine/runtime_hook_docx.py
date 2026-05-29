import sys
import os

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _templates_dir = os.path.join(sys._MEIPASS, 'docx', 'templates')

    import docx.api

    def _frozen_default_docx_path():
        return os.path.join(_templates_dir, 'default.docx')

    docx.api._default_docx_path = _frozen_default_docx_path

    # Patch parts that use __file__-relative paths to find XML templates
    import docx.parts.hdrftr
    import docx.parts.styles
    import docx.parts.comments
    import docx.parts.settings

    def _read_template(name):
        path = os.path.join(_templates_dir, name)
        with open(path, 'rb') as f:
            return f.read()

    def _frozen_footer_xml(cls):
        return _read_template('default-footer.xml')

    def _frozen_header_xml(cls):
        return _read_template('default-header.xml')

    def _frozen_styles_xml(cls):
        return _read_template('default-styles.xml')

    def _frozen_comments_xml(cls):
        return _read_template('default-comments.xml')

    def _frozen_settings_xml(cls):
        return _read_template('default-settings.xml')

    docx.parts.hdrftr.FooterPart._default_footer_xml = classmethod(_frozen_footer_xml)
    docx.parts.hdrftr.HeaderPart._default_header_xml = classmethod(_frozen_header_xml)
    docx.parts.styles.StylesPart._default_styles_xml = classmethod(_frozen_styles_xml)
    docx.parts.comments.CommentsPart._default_comments_xml = classmethod(_frozen_comments_xml)
    docx.parts.settings.SettingsPart._default_settings_xml = classmethod(_frozen_settings_xml)
