from terminaltables import AsciiTable
from proxmoxer import ProxmoxAPI
from csh_ldap import CSHLDAP
from sys import stderr

import secrets

ldap = CSHLDAP(secrets.ldap_user, secrets.ldap_pass)
proxmox = ProxmoxAPI('proxmox01.csh.rit.edu', user=secrets.pm_user, password=secrets.pm_pass, verify_ssl=False)

dues_table = [
    ["User", "#", "CPU", "RAM", "Disk", "Dues"]
]

users = {}
inactive_users = []

def is_active(member):
    group_list = member.get("memberOf")
    if "cn=active,ou=Groups,dc=csh,dc=rit,dc=edu" in group_list:
        return True
    return False


for vm in proxmox.cluster.resources.get(type="vm"):
    if 'pool' in vm:
        if vm['pool'] in users:
            users[vm['pool']].append(vm)
        else:
            users[vm['pool']] = [vm]

# We don't care about drink.
del users['drink']

# Go ahead and try to charge the RTPs...
del users['rtp']

for user in users:
    try:
        ldap_user = ldap.get_member(user, uid=True)
        if not is_active(ldap_user):
            total_mem = 0
            total_cpu = 0
            total_dsk = 0
            cost = 50
            for vm in users[user]:
                total_mem += vm['maxmem']
                total_cpu += vm['maxcpu']
                total_dsk += vm['maxdisk']

            total_mem = round(float(total_mem)/1024**3, 1)
            total_dsk = round(float(total_dsk)/1024**3, 1)

            if total_mem >= 2:
                cost += (total_mem - 2) * 10
            if total_cpu >= 2:
                cost += (total_cpu - 2) * 10
            if total_dsk >= 50:
                cost += ((total_dsk - 50) / 50) * 10

            inactive_users.append(ldap_user.displayName)

            dues_table.append(
                [ldap_user.displayName, len(users[user]), total_cpu, total_mem, total_dsk, int(cost)]
            )
    except KeyError:
        if user == 'alumni':
            for vm in users['alumni']:
                ldap_user = ldap.get_member(vm['name'], uid=True)
                cost = 50
                mem = round(float(vm['maxmem'])/1024**3, 1)
                dsk = round(float(vm['maxdisk'])/1024**3, 1)

                if mem >= 2:
                    cost += (mem - 2) * 10
                if vm['maxcpu'] >= 2:
                    cost += (vm['maxcpu'] - 2) * 10
                if dsk >= 50:
                    cost += ((dsk - 50) / 50) * 10
                dues_table.append([ldap_user.displayName, "1", vm['maxcpu'], mem, dsk, int(cost)])

table = AsciiTable(dues_table)
print(table.table)
stderr.write("The following users are no longer active, please consider migrating their VMs to the alumni pool:\n")
for user in inactive_users:
    stderr.write("  - " + user + "\n")
