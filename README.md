#lixian_api
基于迅雷离线网页版开发的python接口  
##classmethod
thunder_lixian.**login**(username, password, verify_key=None, verify_type='SEA', verifycode=None)  
####param

    username:用户名
    password:密码
    verify_key:获取验证码时响应头中的cookie
    verify_type:获取验证码时响应头中的cookie
    verifycode:验证码

####return

    None

thunder_lixian.**get_lixian_url**(url, verify_key=None, verify_type='SEA', verifycode=None)  
####param

    url:http,ftp,thunder,magnet都行
    verify_key:获取验证码时响应头中的cookie
    verify_type:获取验证码时响应头中的cookie
    verifycode:验证码

####return

    下载链接
  
##License
lixian_api is licensed under GNU Lesser General Public License. You may get a copy of the GNU Lesser General Public License from <http://www.gnu.org/licenses/lgpl.txt>
