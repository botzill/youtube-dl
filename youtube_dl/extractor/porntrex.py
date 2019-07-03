from __future__ import unicode_literals

import datetime
import re

from .common import InfoExtractor
from ..utils import (
    sanitized_Request,
    get_elements_by_class,
    get_element_by_class,
    get_element_by_attribute
)


def string_to_delta(relative):
    # using simplistic year (no leap months are 30 days long.
    # WARNING: 12 months != 1 year
    unit_mapping = [('mic', 'microseconds', 1),
                    ('millis', 'microseconds', 1000),
                    ('sec', 'seconds', 1),
                    ('day', 'days', 1),
                    ('week', 'days', 7),
                    ('mon', 'days', 30),
                    ('year', 'days', 365)]
    try:
        tokens = relative.lower().split(' ')
        past = False
        if tokens[-1] == 'ago':
            past = True
            tokens = tokens[:-1]
        elif tokens[0] == 'in':
            tokens = tokens[1:]

        units = dict(days=0, seconds=0, microseconds=0)
        # we should always get pairs, if not we let this die and throw an exception
        while len(tokens) > 0:
            value = tokens.pop(0)
            if value == 'and':  # just skip this token
                continue
            else:
                value = float(value)

            unit = tokens.pop(0)
            for match, time_unit, time_constant in unit_mapping:
                if unit.startswith(match):
                    units[time_unit] += value * time_constant
        return datetime.timedelta(**units), past

    except Exception as e:
        raise ValueError("Don't know how to parse %s: %s" % (relative, e))


class PornTrexIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?porntrex\.com/video/(?P<id>\d+)/(?P<display_id>[^/?#&]+)'
    _TESTS = [
        {
            'url': 'https://www.porntrex.com/video/781815/black-angelika-cayenne-klein-teens-vs-milfs-2-2015',
            'md5': 'aaa4b8890bf0ea9bb76a8588da79b65a',
            'info_dict': {
                'id': '781815',
                'display_id': 'black-angelika-cayenne-klein-teens-vs-milfs-2-2015',
                'ext': 'mp4',
                'title': 'Black Angelika & Cayenne Klein - Teens vs MILFs 2 (2015',
                'description': 'Black Angelika & Cayenne Klein - Teens vs MILFs 2 (2015)',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'RedB',
                'upload_date': str,
                'average_rating': float,
                'view_count': int,
                'comment_count': int,
                'duration': int,
                'categories': list,
                'tags': list,
                'age_limit': 18,
            },
        },
        {
            'url': 'https://www.porntrex.com/video/392892/gia-derza-anal-teen-newbie',
            'md5': '049480ff1bc2b4bc5a5bdad16763adea',
            'info_dict': {
                'id': '392892',
                'display_id': 'gia-derza-anal-teen-newbie',
                'ext': 'mp4',
                'title': 'Gia Derza - Anal Teen Newbie',
                'description': 'Gia Derza - Anal Teen Newbie',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': '',
                'upload_date': str,
                'average_rating': float,
                'view_count': int,
                'comment_count': int,
                'categories': list,
                'duration': int,
                'tags': list,
                'age_limit': 18,
            },
        }
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        request = sanitized_Request(url)
        request.add_header('Cookie', 'age_verified=1')
        request.add_header('Referer', url)
        webpage = self._download_webpage(request, display_id)

        title = self._html_search_regex(
            r'(?s)<p[^>]+class=["\']title-video[^>]+>(.+?)</p>',
            webpage, 'title', default=None) or self._og_search_title(
            webpage, default=None) or self._html_search_meta(
            'title', webpage, fatal=True)

        page_data = self._search_regex(
            r'flashvars\s*=\s*(\{.+?\});', webpage,
            'media definitions', default='[]', flags=re.MULTILINE | re.DOTALL)
        page_data = page_data.replace('\t', '').replace('\n', '').replace("'", '"')
        page_data = re.sub(r'([a-z1-9_]+):\s+', '"\\1": ', page_data)
        page_data = self._parse_json(page_data, video_id, fatal=False)

        formats = []
        for key, value in page_data.items():
            if (key.startswith('video_url') or re.match(r'^video_alt_url\d+$', key)) and not key.endswith('_text'):
                item = {
                    'url': value,
                    'format_id': page_data['%s_text' % key]
                }
                formats.append(item)

        self._sort_formats(formats)

        description = self._og_search_description(webpage, default=None)
        thumbnail = self._og_search_thumbnail(webpage)
        if thumbnail.startswith('//'):
            thumbnail = 'https:%s' % thumbnail

        categories = get_elements_by_class('js-cat', webpage)

        average_rating = self._html_search_regex(
            r'<span.+?data-rating=["\'](.+?)["\'](.+?)>',
            get_element_by_class('scale', webpage),
            'average rating',
            default='0'
        )
        average_rating = float(average_rating)

        view_count = self._html_search_regex(
            r'<i class=["\'].+?fa-eye["\']></i>\s*<em class="badge">(.+?)</em>',
            webpage,
            'view count',
            default='0'
        )
        view_count = int(view_count.replace(' ', ''))

        comment_count = self._html_search_regex(
            r'.+?Comments\s+\(([\d\s]+)\)',
            get_element_by_attribute('href', '.list-comments', webpage) or '',
            'view count',
            default='0'
        )
        comment_count = int(comment_count.replace(' ', ''))

        uploader = self._html_search_regex(
            r'<a.+?>(.+?)</a>.+?',
            get_element_by_class('username', webpage),
            'uploader',
            flags=re.M | re.DOTALL,
            default=''
        )

        tags = re.findall(r'<a href=["\'].+?/tags/.+?["\']>(.+?)</a>', webpage)
        if tags:
            tags = tags[1:]

        upload_date = self._html_search_regex(
            r'<i class=["\'].+?fa-calendar["\']></i>\s*<em class="badge">(.+?)</em>',
            webpage,
            'uploaded date',
        )
        upload_date = upload_date.strip()

        dt, _ = string_to_delta(upload_date)

        upload_date = datetime.datetime.now() - dt
        upload_date = upload_date.strftime('%Y%m%d')

        duration_frm = re.search(
            r'<i class=["\'].+?fa-clock-o["\']></i>\s*<em class="badge">(?P<min>\d+)min\s*(?P<sec>\d+)sec</em>',
            webpage)
        duration_frm = duration_frm.groupdict()
        duration = int(duration_frm['min']) * 60 + int(duration_frm['sec'])

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'upload_date': upload_date,
            'average_rating': average_rating,
            'view_count': view_count,
            'comment_count': comment_count,
            'categories': categories,
            'duration': duration,
            'tags': tags,
            'formats': formats,
            'age_limit': 18
        }
