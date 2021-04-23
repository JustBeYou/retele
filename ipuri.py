from datetime import datetime

print ("Protocol calculare IP-uri")

"""
Format fisier
<ip baza>/<masca>
<nume retea de start>
<numele retelei unde se afla serverul>
<numar retele>
<nume retea> <useri>
...
<numar legaturi>
<nume retea> <nume retea>
...
"""

# Domeniul este INFO.RO

# pentru pc-uri se aloca de la RA+DEFAULT_START_IP
DEFAULT_START_IP = 10

border = " " + "=" * 35 + " "

switch_template = open("switch_template.txt").read()

def main():
    f = open("input.txt")
    content = f.read().split("\n")

    ip_baza = content[0].strip()
    start = content[1].strip()
    server_location = content[2].strip() 
    details = '\n'.join(content[3:])

    # calculare base address
    base_addr = pasul1(ip_baza)
    
    # calculare puteri si adrese
    g, m = read_graph(details)
    new_base_addr = pasul2(g, base_addr, m)
    
    # configurare retele si legaturi
    pasul3(g, start, new_base_addr, server_location)

def pasul1(ip_s):
    ip, mask = parse_ip(ip_s)

    NA = network_addr(ip, mask)
    BA = broadcast_addr(ip, mask)
    min_addr = NA+1
    max_addr = BA-1

    print ("[!] Pasul 1"+border)
    print (f"NA: {ip_str(NA, mask)}")
    print (f"BA: {ip_str(BA, mask)}")
    print (f"RA: {ip_str(min_addr, mask)} - {ip_str(max_addr, mask)}")
    print ()

    return NA
    
def pasul2(g, base_addr, m):
    print ("[!] Pasul 2"+border)
    
    ls = sort_dict(g)
    caddr = base_addr
    for k,v in ls:
        if v.value == 0: continue # ignoram routerele singure
        p = find_power(v.value+2) # + 2 hosturi pentru gateway si broadcast
        mask = 32 - p
        print (f"{k} 2^{p-1} <= {v.value} <= 2^{p} -> masca {mask}")

        g[k].mask = mask
        g[k].NA = network_addr(caddr, mask)
        g[k].BA = broadcast_addr(caddr, mask)
        g[k].RA = [g[k].NA+1, g[k].BA-1]

        caddr = g[k].BA+1

    print (f"Plus inca {m}: 2^{1} <= 2 <= 2^{2} -> masca 30 pentru conexiuni intre retele")
    print ()

    return caddr
    
def pasul3(g, fst, base_addr, server_location):
    print ("[!] Pasul 3"+border)
    
    ls = sort_dict(g)
    for k,v in ls:
        g[k].dns = g[k].email = g[server_location].RA[1] # ultima adresa in retea
    
        if g[k].value==0: continue
        print (g[k])

    dfs(g[fst], base_addr)

    print ()

# string -> int, int
def parse_ip(s):
    ip, mask = s.split('/')
    ip = list_to_num(map(int, ip.split('.')))
    mask = int(mask)
    return ip, mask

# ops on list repr
def list_to_bits(l):
    return ''.join(map(lambda x: bin(x)[2:].rjust(8, '0'), l))

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

def list_to_num(l):
    return int(list_to_bits(l), 2)

# ops on str repr

# str -> list
def bits_to_list(bits):
    return list(map(lambda x: int(x, 2), chunks(bits, 8)))

# ops on num repr

# num -> list
def num_to_list(n):
    return bits_to_list(bin(n)[2:].rjust(32, '0'))

masks = [0]     # for & 111000...
rev_masks = [0] # for | ...000111
for i in range(1, 32+1):
    masks.append(masks[i-1] | (1 << (32 - i)))
    rev_masks.append((rev_masks[i-1] << 1) | 1)

def apply_mask(ip, mask):
    return ip & masks[mask]

def apply_rev_mask(ip, mask):
    return ip | rev_masks[32 - mask]

def network_addr(ip, mask):
    return apply_mask(ip, mask)

def broadcast_addr(ip, mask):
    return apply_rev_mask(ip, mask)

# num -> str
def ip_str(ip, mask = None):
    return '.'.join(map(str, num_to_list(ip))) + ("" if mask is None else '/' + str(mask))

# num -> str
def mask_str(mask):
    mask_bits = ("1"*mask).ljust(32, '0')
    mask_addr = bits_to_list(mask_bits)
    mask_addr = '.'.join(map(str, mask_addr))
    return mask_addr

class NetworkNode:
    def __init__(self, name, value = 1):
        self.name = name
        self.value = value
        self.neighbours = []
        self.NA = 0
        self.BA = 0
        self.RA = [0, 0]
        self.mask = 0
        self.dns = 0
        self.email = 0

    def connect(self, node):
        self.neighbours.append(node)

    def __lt__(self, other):
        return self.value < other.value

    def __repr__(self):
        mask_addr = mask_str(self.mask)
        gateway = ip_str(self.RA[0])
        
        config_switch = "* Configurare Switch (CLI):\n"
        config_switch += switch_template
        config_switch = config_switch.replace("<HOSTNAME>", f"Sw{self.name.capitalize()}")
        config_switch = config_switch.replace("<GATEWAY>", gateway)
        config_switch = config_switch.replace("<BANNER>", "Sedinta luni")
        config_switch = config_switch.replace("<CURRENT_TIME>", datetime.now().strftime("%H:%M:%S %d %h %Y"))
        config_switch = config_switch.replace("<NETWORK_ADDRESS>", ip_str(self.NA, self.mask))
        config_switch = config_switch.replace("<SWITCH_ADDRESS>", ip_str(self.RA[0]+1)) # switch-ul e la +1
        config_switch = config_switch.replace("<MASK_ADDRESS>", mask_addr)
        
        return (f"--- --- ---\n{self.name} ({self.value})\n"
                + f"NA: {ip_str(self.NA, self.mask)}\n"
                + f"BA: {ip_str(self.BA, self.mask)}\n"
                + f"RA: {ip_str(self.RA[0], self.mask)} - {ip_str(self.RA[1], self.mask)}\n"
                + f"Mask: {mask_addr}\n\n"
                + f"* Configurare PC (GUI):\n"
                + f"IP: {ip_str(self.RA[0]+DEFAULT_START_IP)} Mask: {mask_addr}\n" 
                + f"Gateway: {gateway} DNS: {ip_str(self.dns)}\n"
                + f"* Configurare PC Email (GUI): \n"
                + f"Name: {self.name} Email: {self.name}@INFO.ro \n"
                + f"Server: {ip_str(self.email)}\n"
                + f"Username: {self.name} Password: 123456\n\n"
                + config_switch + "\n\n"
                + "--- --- ---\n\n")

def read_graph(text):
    lines = text.split('\n')
    n = int(lines[0])

    gmap = {}
    for i in range(n):
        line_idx = i + 1
        line = lines[line_idx]
        line = line.split(' ')

        name = line[0]
        value = int(line[1])
        gmap[name] = NetworkNode(name, value)

    m = int(lines[n+1])
    for i in range(m):
        line_idx = i + n + 2
        line = lines[line_idx]
        line = line.split(' ')

        name1, name2 = line[0], line[1]
        gmap[name1].connect(gmap[name2])

    return gmap, m

def sort_dict(x):
    return sorted(x.items(), key=lambda item: item[1], reverse=True)

def find_power(val):
    for i in range(32):
        if 2**i <= val and val <= 2**(i+1):
            return i+1
    return -1

def dfs(node, base_addr):
    for neigh in node.neighbours:
        print(f"{node.name} - {neigh.name}")

        mask = 30
        NA = network_addr(base_addr, mask)
        BA = broadcast_addr(base_addr, mask)
        min_addr = NA+1
        max_addr = BA-1

        print (f"NA: {ip_str(NA, mask)}")
        print (f"BA: {ip_str(BA, mask)}")
        print (f"RA: {ip_str(min_addr, mask)} - {ip_str(max_addr, mask)}")
        mask_bits = ("1"*mask).ljust(32, '0')
        mask_addr = bits_to_list(mask_bits)
        mask_addr = '.'.join(map(str, mask_addr))
        print (f"Mask: {mask_addr}")
        print ()
        
        base_addr = dfs(neigh, BA+1)
    return base_addr

if __name__ == "__main__":
    main()
