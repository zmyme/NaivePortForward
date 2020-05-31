from network import PortForwardServer
import parallel
import console

if __name__ == '__main__':
    server = PortForwardServer()

    def command_status(args):
        num_free, num_busy, num_all = parallel.daemon.status()
        print('ALL: {0}'.format(num_all))
        print('FREE: {0}'.format(num_free))
        print('BUSY: {0}'.format(num_busy))
    def command_add(args):
        listen, dst = args.split('>')
        listen = listen.split(':')
        if len(listen) == 2:
            listen_ip, listen_port = listen
            listen_port = int(listen_port)
        elif len(listen) == 1:
            listen_ip = '0.0.0.0'
            listen_port = int(listen[0])
        else:
            print('unknown input:', listen)
        dst_ip, dst_port = dst.split(':')
        dst_port = int(dst_port)
        print('dst_ip: {0} [fmt={1}]'.format(dst_ip, type(dst_ip)))
        print('dst_port: {0} [fmt={1}]'.format(dst_port, type(dst_port)))
        print('listen_ip: {0} [fmt={1}]'.format(listen_ip, type(listen_ip)))
        print('listen_port: {0} [fmt={1}]'.format(listen_port, type(listen_port)))
        server.add(dst_ip, dst_port, listen_ip, listen_port)
    def command_ls(args):
        lists = server.get_rules()
        for i, l in enumerate(lists):
            print('[{0}] {1}'.format(i+1, l))
    def command_delete(args):
        index = None
        try:
            index = int(args)
        except:
            print('Error: delete command should be followed by a int value.')
        if index > len(server.get_rules()):
            print('Error: index too large for only {0} rules.'.format(len(server.get_rules())))
        elif index <= 0:
            print('Error: Invalid index {0}'.format(index))
        else:
            server.delete(index-1)

    con = console.console('PortForward')
    con.regist('status', action=command_status, help_info='show parallel daemon status.')
    con.regist('add', action=command_add, help_info='Add new port forward, format:\n\t[listen_ip:]listen_port>dst_ip:dst_port')
    con.regist('ls', action=command_ls, help_info='Show current port forward rules.', alias=['show'])
    con.regist('delete', action=command_delete, help_info='delete a rule.', alias=['del'])
    con.interactive()
