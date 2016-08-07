import json
import requests
import time
from random import random
import logging


# refer:引用自binux
def _now():
    return int(time.time() * 1000)


# refer:引用自binux
def _random():
    return str(_now()) + str(random() * (2000000 - 10) + 10)


def _strip_sig(content):
    start = content.find('(')
    if start == -1:
        return None
    if content[len(content) - 1] != ')':
        return None
    return content[start + 1:-1]


def _parse_recursive(content):
    content = _strip_sig(content)
    res = []
    args = iter(content.split(','))
    for x in args:
        x = x.strip(" '")
        if x.startswith('new Array'):
            while x[-1] != ')':
                x += ',' + next(args).strip(" '")
            res.append(_parse_recursive(x))
        else:
            res.append(x)
    return res


def _js_args_parse(parm, content):
    args = _parse_recursive(content)
    return {x: y for x, y in zip(parm, args)}


def _js_json_parse(content):
    return json.loads(_strip_sig(content))


class api_exception(Exception):
    pass


class thunder_lixian:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = r'Mozilla/5.0 (X11; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0'
        self._is_login = False
        self.gdriveid = None

    def login(self, username, password, verify_key=None, verify_type='SEA', verifycode=None):
        if self._is_login:
            raise api_exception('已经登陆,不能再登陆')

        check_res = self._check_user(username)
        if check_res:  # 不需要验证码
            login_res = self._post_login(username, password, check_res)
            if login_res:
                raise api_exception(login_res)
        else:
            if verify_key and verify_type and verifycode:
                self.session.cookies['VERIFY_KEY'] = verify_key
                self.session.cookies['verify_type'] = verify_type
                login_res = self._post_login(username, password, verifycode)
                self.session.cookies['VERIFY_KEY'] = None
                self.session.cookies['verify_type'] = None
                if login_res:
                    raise api_exception(login_res)
            else:
                raise api_exception('需要验证码')
        # 获取gdriveid
        self._showtask_unfresh()
        self._is_login = True
        # 修改列表条目
        self.session.cookies['pagenum'] = '100'

    _check_url = 'http://login.xunlei.com/check?u={username}&cachetime={time}'

    def _check_user(self, username):
        r = requests.get(self._check_url.format(username=username, time=_now()))
        if r.cookies['check_result'] == '1':  # need verify code
            return None
        else:
            return r.cookies['check_result'].split(':')[1]

    _login_url = 'https://login.xunlei.com/sec2login/'

    def _post_login(self, username, password, verifycode):
        time.sleep(2)
        login_data = {
            'u': username,
            # 'p': _hex_md5(_hex_md5(_hex_md5(password)) + verifycode.upper()),
            'p': password,
            'verifycode': verifycode,
            'login_enable': '0',
            'business_type': '108',
            'v': '101',
            'cachetime': str(_now())
        }
        r = self.session.post(self._login_url, data=login_data)

        logging.debug(r.content)

        if 'logindetail' in r.cookies:  # login fail
            err_code = r.cookies['logindetail'].split(':')[0]
            if err_code == '403':
                return '验证码错误'
            elif err_code == '412':
                return '密码错误'
            else:
                return r.cookies['logindetail']
        else:
            return None

    def get_lixian_url(self, url, verify_key=None, verify_type='SEA', verifycode=None):
        if not self._is_login:
            raise api_exception('请先登陆')
        # 获取链接的基本信息
        if url.startswith('magnet:'):
            url_info = self._url_query(url)
        else:
            url_info = self._task_check(url)

        if url_info is None:
            raise api_exception('非法的链接')

        # 提交
        if verify_key and verifycode:
            self.session.cookies['VERIFY_KEY'] = verify_key
            self.session.cookies['verify_type'] = verify_type

        if url.startswith('magnet:'):
            task_id = self._bt_task_commit(url_info, verifycode)
        else:
            task_id = self._task_commit(url, url_info, verifycode)

        if verify_key and verifycode:
            self.session.cookies['VERIFY_KEY'] = None
            self.session.cookies['verify_type'] = None

        if task_id is None:
            raise api_exception('需要验证码')

        # 获取url
        if url.startswith('magnet:'):
            lixian_url = self._fill_bt_list(task_id, url_info)
        else:
            lixian_url = [self._task_process(task_id)]

        if lixian_url is None:
            raise api_exception('任务还未离线完成')
        return lixian_url

    _task_check_url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_check'

    def _task_check(self, url):
        r = self.session.get(self._task_check_url, params={
            'callback': 'queryCid',
            'url': url,
            'interfrom': 'task',
            'random': _random(),
            'tcache': _now()
        })
        r.raise_for_status()
        parms = ['cid', 'gcid', 'file_size', 'avail_space', 'tname', 'goldbean_need', 'silverbean_need', 'is_full',
                 'random', 'type', 'rtcode']
        return _js_args_parse(parms, r.content.decode('utf-8'))

    _url_query_url = 'http://dynamic.cloud.vip.xunlei.com/interface/url_query'

    def _url_query(self, url):
        r = self.session.get(self._url_query_url, params={
            'callback': 'queryUrl',
            'u': url,
            'interfrom': 'task',
            'random': _random(),
            'tcache': _now()
        })
        r.raise_for_status()
        parms = ['flag', 'infohash', 'fsize', 'bt_title', 'is_full', 'subtitle', 'subformatsize', 'size_list',
                 'valid_list', 'file_icon', 'findex', 'is_blocked', 'random', 'rtcode']
        res = _js_args_parse(parms, r.text)
        if res['flag'] == '0':
            return None
        else:
            return res

    _task_commit_url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_commit'

    def _task_commit(self, url, info, verifycode):
        r = self.session.get(self._task_commit_url, params={
            'callback': 'ret_task',
            'uid': self.session.cookies['userid'],
            'cid': info['cid'],
            'gcid': info['gcid'],
            'size': info['file_size'],
            'goldbean': 0,
            'silverbean': 0,
            't': info['tname'],
            'url': url,
            'verify_code': verifycode,
            'type': 0,
            'o_page': 'history',
            'o_taskid': 0,
            'lass_id': 0,
            'database': 'undefined',
            'interfrom': 'task',
            'time': 'Fri%20Jul%2029%202016%2011:38:04%20GMT+0800',
            'noCacheIE': _now()
        })
        r.raise_for_status()
        parms = ['ret_num', 'taskid', 'time']
        args = _js_args_parse(parms, r.content.decode('utf-8'))
        if args['ret_num'] == -12 or args['ret_num'] == -11:  # 出验证码
            return None
        return args['taskid']

    _task_process_url = 'http://dynamic.cloud.vip.xunlei.com/interface/task_process?callback=jsonp1470562464775&t=Sun%20Aug%2007%202016%2017:43:26%20GMT+0800%20(CST)'

    def _task_process(self, tid):
        r = self.session.post(self._task_process_url, data={
            'list': tid,  # 可以批量
            'nm_list': tid,  # 可以批量
            'bt_list': '',
            'uid': self.session.cookies['userid'],
            'interfrom': 'task'
        })
        r.raise_for_status()
        json_res = _js_json_parse(r.text)
        lixian_url = json_res['Process']['Record'][0]['lixian_url']
        if lixian_url == '':
            return None
        return lixian_url

    _bt_task_commit_url = 'http://dynamic.cloud.vip.xunlei.com/interface/bt_task_commit?callback=jsonp1470230995939&t=Wed%20Aug%2003%202016%2022:10:20%20GMT+0800'

    def _bt_task_commit(self, info, verifycode):
        r = self.session.post(self._bt_task_commit_url, data={
            'uid': self.session.cookies['userid'],
            'btname': info['bt_title'],
            'cid': info['infohash'],
            'goldbean': 0,
            'silverbean': 0,
            'tsize': info['fsize'],
            'findex': '_'.join(info['findex']) + '_',
            'size': '_'.join(info['size_list']) + '_',
            'o_taskid': 0,
            'o_page': 'task',
            'class_id': 0,
            'interfrom': 'task',
            'verify_code': verifycode
        })
        r.raise_for_status()
        res_json = _js_json_parse(r.text)
        if res_json['progress'] != 1:
            return None
        return res_json['id']

    _showtask_unfresh_url = 'http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh'

    def _showtask_unfresh(self):
        r = self.session.get(self._showtask_unfresh_url, params={
            'callback': 'jsonp1470122229847',
            't': 'Fri%20Jul%2029%202016%2011:38:04%20GMT+0800',
            'type_id': 4,
            'page': 1,
            'tasknum': 30,
            'p': 1,
            'interfrom': 'task'
        })
        r.raise_for_status()
        json_res = _js_json_parse(r.content.decode('utf-8'))
        self.gdriveid = 'gdriveid=' + json_res['info']['user']['cookie']

    _fill_bt_list_url = 'http://dynamic.cloud.vip.xunlei.com/interface/fill_bt_list'

    # 返回[urls]
    def _fill_bt_list(self, tid, info):
        item_num = len(info['findex'])
        results = []
        has_url = False
        now_page = 1
        while item_num > 0:
            r = self.session.get(self._fill_bt_list_url, params={
                'callback': 'fill_bt_list',
                'tid': tid,
                'infoid': info['infohash'],
                'g_net': 1,
                'p': now_page,
                'uid': self.session.cookies['userid'],
                'interfrom': 'task',
                'noCacheIE': _now()
            })
            r.raise_for_status()
            json_res = _js_json_parse(r.text)
            records = json_res['Result']['Record']
            for rec in records:
                results.append(rec['downurl'])
                if results[-1] != '':
                    has_url = True

            item_num -= json_res['Result']['btpernum']
            now_page += 1

        if has_url:
            return results
        else:
            return None

