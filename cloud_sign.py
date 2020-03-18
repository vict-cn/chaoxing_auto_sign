# -*- coding: utf8 -*-
import os
import asyncio
import re
import json
import requests

user_info = {
	'username': 'xxxx',
	'password': 'xxxx',
	'schoolid': ''  # 学号登录才需要填写
}

cookies_path = "cookies.json"  # cookies.json 保存路径


class AutoSign(object):

	def __init__(self, username, password, schoolid=None):
		"""初始化就进行登录"""
		self.headers = {
			'Accept-Encoding': 'gzip, deflate',
			'Accept-Language': 'zh-CN,zh;q=0.9',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'}
		self.session = requests.session()
		self.session.headers = self.headers
		# 读取指定用户的cookies
		if self.check_cookies_status(username) is False:
			self.login(password, schoolid, username)
			self.save_cookies(username)

	def save_cookies(self, username):
		"""保存cookies"""
		new_cookies = self.session.cookies.get_dict()
		with open(cookies_path, "r") as f:
			data = json.load(f)
			data[username] = new_cookies
			with open(cookies_path, 'w') as f2:
				json.dump(data, f2)

	def check_cookies_status(self, username):
		"""检测json文件内是否存有cookies,有则检测，无则登录"""
		if "cookies.json" not in os.listdir("./"):
			with open(cookies_path, 'w+') as f:
				f.write("{}")

		with open(cookies_path, 'r') as f:

			# json文件有无账号cookies, 没有，则直接返回假
			try:
				data = json.load(f)
				cookies = data[username]
			except Exception:
				return False

			# 找到后设置cookies
			for u in cookies:
				self.session.cookies.set(u, cookies[u])

			# 检测cookies是否有效
			r = self.session.get('http://i.mooc.chaoxing.com/app/myapps.shtml', allow_redirects=False)
			if r.status_code != 200:
				print("cookies已失效，重新获取中")
				return False
			else:
				print("cookies有效哦")
				return True

	def login(self, password, schoolid, username):
		# 登录-手机邮箱登录
		if schoolid:
			r = self.session.post(
				'http://passport2.chaoxing.com/api/login?name={}&pwd={}&schoolid={}&verify=0'.format(username, password,
				                                                                                     schoolid))
			if json.loads(r.text)['result']:
				print("登录成功")
			else:
				print("登录失败，请检查账号密码是否正确")

		else:
			r = self.session.get(
				'https://passport2.chaoxing.com/api/login?name={}&pwd={}&schoolid=&verify=0'.format(username, password),
				headers=self.headers)
			if json.loads(r.text)['result']:
				print("登录成功")
			else:
				print("登录失败，请检查账号密码是否正确")

	def get_all_classid(self) -> list:
		"""获取课程主页中所有课程的classid和courseid"""
		re_rule = r'<li style="position:relative">[\s]*<input type="hidden" name="courseId" value="(.*)" />[\s].*<input type="hidden" name="classId" value="(.*)" />[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[\s].*[s].*[\s]*[\s].*[\s].*[\s].*[\s].*[\s].*<a  href=\'.*\' target="_blank" title=".*">(.*)</a>'
		r = self.session.get(
			'http://mooc1-2.chaoxing.com/visit/interaction',
			headers=self.headers)
		res = re.findall(re_rule, r.text)
		return res

	async def get_activeid(self, classid, courseid, classname):
		"""访问任务面板获取课程的活动id"""
		sign_re_rule = r'<div class="Mct" onclick="activeDetail\((.*),2,null\)">[\s].*[\s].*[\s].*[\s].*<dd class="green">.*</dd>'
		r = self.session.get(
			'https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId={}&jclassId={}'.format(
				courseid, classid), headers=self.headers, verify=False)
		res = re.findall(sign_re_rule, r.text)
		if res != []:  # 满足签到条件
			return {
				'classid': classid,
				'courseid': courseid,
				'activeid': res[0],
				'classname': classname}

	def general_sign(self, classid, courseid, activeid, checkcode=None):
		"""普通签到"""
		r = self.session.get(
			'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/preSign?activeId={}&classId={}&fid=39037&courseId={}'.format(
				activeid, classid, courseid), headers=self.headers, verify=False)
		title = re.findall('<title>(.*)</title>', r.text)[0]
		if "签到成功" not in title:
			return "拍照签到"
		else:
			sign_date = re.findall('<em id="st">(.*)</em>', r.text)[0]
			return '[{}]-[{}]'.format(sign_date, '签到成功')

	def hand_sign(self, classid, courseid, activeid):
		"""手势签到"""
		hand_sign_url = "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/signIn?&courseId={}&classId={}&activeId={}".format(
			courseid, classid, activeid)
		r = self.session.get(hand_sign_url, headers=self.headers, verify=False)
		res = re.findall('<title>(.*)</title>', r.text)
		return res[0]

	def qcode_sign(self, activeId):
		"""二维码签到"""
		params = {
			'name': '',
			'activeId': activeId,
			'uid': '',
			'clientip': '',
			'useragent': '',
			'latitude': '-1',
			'longitude': '-1',
			'fid': '',
			'appType': '15'
		}
		response = self.session.get('https://mobilelearn.chaoxing.com/pptSign/stuSignajax', params=params)
		return response.text

	def addr_sign(self, activeId):
		"""位置签到"""
		params = {
			'name': '',
			'activeId': activeId,
			'address': '中国',
			'uid': '',
			'clientip': '0.0.0.0',
			'latitude': '-2',
			'longitude': '-1',
			'fid': '',
			'appType': '15',
			'ifTiJiao': '1'
		}
		response = self.session.get('https://mobilelearn.chaoxing.com/pptSign/stuSignajax', params=params)
		return response.text

	def tphoto_sign(self, activeId):
		"""拍照签到"""
		params = {
			'name': '',
			'activeId': activeId,
			'address': '中国',
			'uid': '',
			'clientip': '0.0.0.0',
			'latitude': '-2',
			'longitude': '-1',
			'fid': '',
			'appType': '15',
			'ifTiJiao': '1',
			'objectId': '5712278eff455f9bcd76a85cd95c5de3'
		}
		res = self.session.get('https://mobilelearn.chaoxing.com/pptSign/stuSignajax', params=params)
		return res.text

	def sign_in(self, classid, courseid, activeid):
		r = self.general_sign(classid, courseid, activeid)
		if "签到成功" in r:
			return r
		elif "手势签到" in r:
			sign_status = self.hand_sign(classid, courseid, activeid)
			return sign_status
		elif "二维码签到" in r:
			return '二维码签到', self.qcode_sign(activeid)
		elif "位置签到" in r:
			return '位置签到', self.addr_sign(activeid)
		elif "拍照签到" in r:
			return '拍照签到', self.tphoto_sign(activeid)

	def run(self):
		"""开始所有签到任务"""
		tasks = []
		# 获取所有课程的classid和course_id
		classid_courseId = self.get_all_classid()

		# 获取所有课程activeid
		for i in classid_courseId:
			coroutine = self.get_activeid(i[1], i[0], i[2])
			tasks.append(coroutine)

		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		result = loop.run_until_complete(asyncio.gather(*tasks))
		sign_msg = ""
		for d in result:
			if d is not None:
				sign_msg += '{}:{}'.format(d['classname'], self.sign_in(
					d['classid'], d['courseid'], d['activeid']))
		return sign_msg


def main_handler(event=None, context=None):
	"""腾讯云函数，执行这个方法"""
	if "username" and "password" in event.keys():
		# api请求
		s = AutoSign(event['username'], event['password'])
	else:
		# 自身函数执行的时候，才执行这个，可用于定时任务
		s = AutoSign(user_info['username'], user_info['password'])
	result = s.run()
	return result


def local_run():
	# 本地运行使用
	s = AutoSign(user_info['username'], user_info['password'])
	result = s.run()
	print(result)
	return result


if __name__ == '__main__':
	local_run()