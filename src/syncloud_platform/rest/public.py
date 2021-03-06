import sys
import traceback

import convertible
import requests
from flask import jsonify, send_from_directory, request, redirect, Flask, Response
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

from syncloud_platform.auth.ldapauth import authenticate
from syncloud_platform.injector import get_injector
from syncloud_platform.rest.props import html_prefix, rest_prefix
from syncloud_platform.rest.flask_decorators import nocache, redirect_if_not_activated
from syncloud_platform.rest.model.flask_user import FlaskUser
from syncloud_platform.rest.model.user import User
from syncloud_platform.gaplib import linux

from syncloud_platform.rest.service_exception import ServiceException

injector = get_injector()
public = injector.public
device = injector.device

app = Flask(__name__)
app.config['SECRET_KEY'] = public.user_platform_config.get_web_secret_key()
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.unauthorized_handler
def _callback():
    if request.is_xhr:
        return 'Unauthorised', 401
    else:
        return redirect(html_prefix + '/login.html')


@app.route(html_prefix + '/<path:filename>')
@nocache
@redirect_if_not_activated
def static_file(filename):
    return send_from_directory(public.www_dir, filename)


@login_manager.user_loader
def load_user(email):
    return FlaskUser(User(email))


@app.route(rest_prefix + "/login", methods=["GET", "POST"])
@redirect_if_not_activated
def login():

    if 'name' in request.form and 'password' in request.form:
        try:
            authenticate(request.form['name'], request.form['password'])
            user_flask = FlaskUser(User(request.form['name']))
            login_user(user_flask, remember=False)
            # next_url = request.get('next_url', '/')
            return redirect("/")
        except Exception, e:
            traceback.print_exc(file=sys.stdout)
            return jsonify(message=e.message), 400

    return jsonify(message='missing name or password'), 400


@app.route(rest_prefix + "/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return 'User logged out', 200


@app.route(rest_prefix + "/user", methods=["GET"])
@login_required
def user():
    return jsonify(convertible.to_dict(current_user.user)), 200


@app.route('/')
@redirect_if_not_activated
@login_required
def index():
    return static_file('index.html')


@app.route(rest_prefix + "/installed_apps", methods=["GET"])
@login_required
def installed_apps():
    return jsonify(apps=convertible.to_dict(public.installed_apps())), 200


@app.route(rest_prefix + "/app", methods=["GET"])
@login_required
def app_status():
    return jsonify(info=convertible.to_dict(public.get_app(request.args['app_id']))), 200


@app.route(rest_prefix + "/install", methods=["GET"])
@login_required
def install():
    public.install(request.args['app_id'])
    return 'OK', 200


@app.route(rest_prefix + "/remove", methods=["GET"])
@login_required
def remove():
    return jsonify(message=public.remove(request.args['app_id'])), 200


@app.route(rest_prefix + "/restart", methods=["GET"])
@login_required
def restart():
    public.restart()
    return 'OK', 200


@app.route(rest_prefix + "/shutdown", methods=["GET"])
@login_required
def shutdown():
    public.shutdown()
    return 'OK', 200


@app.route(rest_prefix + "/upgrade", methods=["GET"])
@login_required
def upgrade():

    force = False
    if 'force' in request.args:
        force = request.args['force'] == 'true'

    channel = 'stable'
    if 'channel' in request.args:
        channel = request.args['channel']

    public.upgrade(request.args['app_id'], channel, force)

    return 'OK', 200


@app.route(rest_prefix + "/check", methods=["GET"])
@login_required
def update():
    return jsonify(message=public.update()), 200


@app.route(rest_prefix + "/available_apps", methods=["GET"])
@login_required
def available_apps():
    return jsonify(apps=convertible.to_dict(public.available_apps())), 200


@app.route(rest_prefix + "/access/port_mappings", methods=["GET"])
@login_required
def port_mappings():
    return jsonify(success=True, port_mappings=convertible.to_dict(public.port_mappings())), 200


@app.route(rest_prefix + "/access/access", methods=["GET"])
@login_required
def access():
    return jsonify(success=True, data=public.access()), 200


@app.route(rest_prefix + "/access/set_access", methods=["GET"])
@login_required
def set_access():
    public_ip = None
    if 'public_ip' in request.args:
        public_ip = request.args['public_ip']
    public.set_access(
        request.args['upnp_enabled'] == 'true',
        request.args['external_access'] == 'true',
        public_ip,
        int(request.args['certificate_port']),
        int(request.args['access_port'])
    )
    return jsonify(success=True), 200


@app.route(rest_prefix + "/access/network_interfaces", methods=["GET"])
@login_required
def network_interfaces():
    return jsonify(success=True, data=dict(interfaces=public.network_interfaces())), 200


@app.route(rest_prefix + "/send_log", methods=["GET"])
@login_required
def send_log():
    include_support = request.args['include_support'] == 'true'
    public.send_logs(include_support)
    return jsonify(success=True), 200


@app.route(rest_prefix + "/settings/device_domain", methods=["GET"])
@login_required
def device_domain():
    return jsonify(success=True, device_domain=public.domain()), 200


@app.route(rest_prefix + "/settings/device_url", methods=["GET"])
@login_required
def device_url():
    return jsonify(success=True, device_url=public.device_url()), 200


@app.route(rest_prefix + "/settings/disks", methods=["GET"])
@login_required
def disks():
    return jsonify(success=True, disks=convertible.to_dict(public.disks())), 200


@app.route(rest_prefix + "/settings/boot_disk", methods=["GET"])
@login_required
def boot_disk():
    return jsonify(success=True, data=convertible.to_dict(public.boot_disk())), 200


@app.route(rest_prefix + "/settings/disk_activate", methods=["GET"])
@login_required
def disk_activate():
    return jsonify(success=True, disks=public.disk_activate(request.args['device'])), 200


@app.route(rest_prefix + "/storage/disk_format", methods=["POST"])
@login_required
def disk_format():
    return jsonify(success=True, disks=public.disk_format(request.form['device'])), 200


@app.route(rest_prefix + "/settings/disk_format_status", methods=["GET"])
@login_required
def disk_format_status():
    return jsonify(is_running=public.disk_format_status()), 200


@app.route(rest_prefix + "/settings/versions", methods=["GET"])
@login_required
def versions():
    return jsonify(success=True, data=convertible.to_dict(public.list_apps())), 200


@app.route(rest_prefix + "/settings/sam_status", methods=["GET"])
@login_required
def sam_status():
    return jsonify(is_running=public.sam_status()), 200


@app.route(rest_prefix + "/settings/boot_extend", methods=["GET"])
@login_required
def boot_extend():
    return jsonify(is_running=public.boot_extend()), 200


@app.route(rest_prefix + "/settings/boot_extend_status", methods=["GET"])
@login_required
def boot_extend_status():
    return jsonify(is_running=public.boot_extend_status()), 200


@app.route(rest_prefix + "/settings/disk_deactivate", methods=["GET"])
@login_required
def disk_deactivate():
    return jsonify(success=True, disks=public.disk_deactivate()), 200


@app.route(rest_prefix + "/settings/regenerate_certificate", methods=["GET"])
@login_required
def regenerate_certificate():
    public.regenerate_certificate()
    return jsonify(success=True), 200


@app.route(rest_prefix + "/settings/activate_url", methods=["GET"])
@login_required
def activate_url():
    return jsonify(activate_url='http://{0}:81'.format(linux.local_ip()), success=True), 200


@app.route(rest_prefix + "/app_image", methods=["GET"])
@login_required
def app_image():
    channel = request.args['channel']
    app = request.args['app']
    r = requests.get('http://apps.syncloud.org/releases/{0}/images/{1}-128.png'.format(channel, app), stream=True)
    return Response(r.iter_content(chunk_size=10*1024),
                    content_type=r.headers['Content-Type'])


@app.errorhandler(Exception)
def handle_exception(error):
    print '-'*60
    traceback.print_exc(file=sys.stdout)
    print '-'*60
    status_code = 500

    if isinstance(error, ServiceException):
        status_code = 200

    response = jsonify(success=False, message=error.message)
    return response, status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
