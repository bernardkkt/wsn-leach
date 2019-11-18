#!/usr/bin/env python3

import time
import logging
import random


class Node:
    uid = str()  # node serial for identification
    remaining_energy = float()  # battery state
    head = bool()  # operation mode: either head or node
    was_head = bool()  # a counter, will be reset in every new round
    head_probability = float()  # probability to become a cluster head
    round_performed = int()  # number of rounds involved in doing work
    max_round = int()

    n_bs_distance = float()  # distance between node and base station

    e_data_agg = float()
    e_tx_fs = float()
    e_tx_mp = float()
    e_tx = float()
    e_rx = float()

    def auto_reset(self):
        self.head = False
        if self.round_performed % round(1 / self.head_probability) == 0:
            self.was_head = False

    def self_elect(self):
        if not self.was_head:  # equals to "if self.was_head == False"
            p = self.head_probability
            r = self.round_performed
            if random.random() <= (p / (1 - p * (r % round(1 / p)))):
                self.head = True
                self.was_head = True
        else:
            self.head = False

    def send(self, d: float):
        d_thres = (self.e_tx_fs / self.e_tx_mp) ** 0.5  # distance threshold
        if d > d_thres:
            self.remaining_energy = self.remaining_energy - ((4000 * self.e_tx) + (4000 * self.e_tx_mp * (d ** 4)))
        else:
            self.remaining_energy = self.remaining_energy - ((4000 * self.e_tx) + (4000 * self.e_tx_fs * (d ** 2)))

    def receive(self):
        self.remaining_energy = self.remaining_energy - (4000 * (self.e_rx + self.e_data_agg))

    def revert_to_node(self):
        self.head = False

    def send_to_bs(self):
        d_thres = (self.e_tx_fs / self.e_tx_mp) ** 0.5  # distance threshold
        if self.n_bs_distance > d_thres:  # use multi-path algorithm
            self.remaining_energy = self.remaining_energy - ((4000 * (self.e_tx + self.e_data_agg)) + 4000 * self.e_tx_mp * (self.n_bs_distance ** 4))
        else:  # use free space algorithm
            self.remaining_energy = self.remaining_energy - (4000 * (self.e_tx + self.e_data_agg)) - (4000 * self.e_tx_fs * (self.n_bs_distance ** 2))


# Initialisation of logger
timestamp = int(time.time())
logger = logging.Logger("main", logging.INFO)
logger.addHandler(logging.StreamHandler())
writer = logging.FileHandler("leach-{}.log".format(timestamp))
logger.addHandler(writer)

# Field set-up
nodes_number = 100  # number of nodes deployed in a WSN
x_dimension = 100  # width of field
y_dimension = 100  # length of field
sink_xy = [50, 50]  # coordinate of sink
node_collection = list()  # all node objects in list

# Get random coordinates for nodes
coordinates = list()
for x in range(nodes_number):
    while True:
        # get a list of random pairs of x and y
        x_val = random.randint(0, x_dimension)
        y_val = random.randint(0, y_dimension)
        if not coordinates.count((x_val, y_val)):  # no overlapping
            coordinates.append((x_val, y_val))
            break

# Populate all nodes into list
while coordinates:
    (x_val, y_val) = coordinates.pop(-1)
    node = dict()
    node["x"] = x_val
    node["y"] = y_val
    node["tx_rx_node"] = None
    node["object"] = Node()
    node_collection.append(node)
logger.info("Number of nodes populated: {}".format(len(node_collection)))

# Node parameter set-up
normal_energy = 0.5  # Initial energy Eo
data_agg_energy = 5 * 10 ** -9  # energy for data aggregation
tx_fs_energy = 10 * 10 ** -12  # energy for free space transmission
tx_mp_energy = 0.0013 * 10 ** -12  # energy for multi-path transmission
tx_energy = 50 * 10 ** -9  # energy for tx
rx_energy = 50 * 10 ** -9  # energy for rx
head_prob = 0.1  # probability to become head
max_round = 10001  # maximum number of turns
for n in node_collection:
    dx2 = (n["x"] - sink_xy[0]) ** 2
    dy2 = (n["y"] - sink_xy[1]) ** 2
    n["object"].n_bs_distance = (dx2 + dy2) ** 0.5
    n["object"].remaining_energy = normal_energy
    n["object"].e_data_agg = data_agg_energy
    n["object"].e_tx_fs = tx_fs_energy
    n["object"].e_tx_mp = tx_mp_energy
    n["object"].e_tx = tx_energy
    n["object"].e_rx = rx_energy
    n["object"].was_head = False
    n["object"].head_probability = head_prob
    n["object"].round_performed = 0
    n["object"].max_round = max_round

# Values for heterogeneity (energy)
surplus_energy_node_percentage = 10 / 100  # fraction of nodes with advanced power
surplus_energy_factor = 1  # alpha: amount of the surplus energy in each advanced node; final = Eo(1+a)
surplus_nodes = nodes_number * surplus_energy_node_percentage
advanced_list = list()
for x in range(int(surplus_nodes)):
    while True:
        n = random.choice(node_collection)
        if n["object"].remaining_energy == normal_energy:
            n["object"].remaining_energy = normal_energy * (1 + surplus_energy_factor)
            advanced_list.append(n)
            break

# Cycle starts
dead_node = list()  # list of dead nodes
min_distance = float()  # the minimum distance between any 2 cluster heads
stats = list()  # for statistics purpose
for x in range(max_round):
    logger.info("Round {}:".format(x))
    # Check remaining energy
    for n in node_collection:
        if n["object"].remaining_energy <= 0:
            dead_node.append(n)
            logger.info("Dead nodes: {} out of {}".format(len(dead_node), nodes_number))
    for n in dead_node:
        if node_collection.count(n):
            node_collection.remove(n)

    # Premature death of WSN before reaching the last round
    if not node_collection:  # if there are no working nodes left
        logger.info("Round {}: No more working nodes left in the network.".format(x))
        break

    # Nomination/Election
    cluster = list()
    for n in node_collection:
        n["object"].round_performed = x
        n["object"].auto_reset()  # Reset cluster head history at new epoch
        n["object"].self_elect()  # Attempt to promote itself as head
        if n["object"].head:  # if selected as head
            # n["object"].send_to_bs()
            cluster.append(n)
    # plt.figure(1)
    # plt.plot([x["x"] for x in cluster], [x["y"] for x in cluster], "ro", markersize=80, alpha=0.5)
    # plt.plot([x["x"] for x in node_collection], [x["y"] for x in node_collection], "k.")

    # Optimisation
    whitelist = list()  # list of cluster heads to be preserved
    blacklist = list()  # list of cluster heads to revert to normal nodes
    min_distance = (((x_dimension ** 2) + (y_dimension ** 2)) ** 0.5) * 0.2
    while cluster:
        c = random.choice(cluster)  # simulating communication with BS in random queue
        whitelist.append(cluster.pop(cluster.index(c)))
        if cluster:
            for item in cluster:
                dx2 = (c["x"] - item["x"]) ** 2
                dy2 = (c["y"] - item["y"]) ** 2
                if min_distance >= (dx2 + dy2) ** 0.5:  # cluster head is disqualified and turns into (node)
                    blacklist.append(item)
                    node_collection[node_collection.index(item)]["object"].revert_to_node()
            while blacklist:
                cluster.remove(blacklist.pop(-1))
    cluster = whitelist
    for c in cluster:
        node_collection[node_collection.index(c)]["object"].send_to_bs()
    logger.info("Number of cluster heads: {}".format(len(cluster)))
    # plt.figure(2)
    # plt.plot([x["x"] for x in cluster], [x["y"] for x in cluster], "ro", markersize=80, alpha=0.5)
    # plt.plot([x["x"] for x in node_collection], [x["y"] for x in node_collection], "k.")
    # plt.show()

    # Establishment
    if cluster:  # if there is at least one cluster
        for n in node_collection:
            if not n["object"].head:  # if the node is not head
                # Identify which node/sink to receive message sent from n
                n["tx_rx_node"] = None
                min_dis = n["object"].n_bs_distance
                for c in cluster:
                    dx2 = (n["x"] - c["x"]) ** 2
                    dy2 = (n["y"] - c["y"]) ** 2
                    distance = (dx2 + dy2) ** 0.5
                    if distance < min_dis:
                        min_dis = distance
                        n["tx_rx_node"] = c

                # Data Transfer
                if n["tx_rx_node"] is None:
                    # Base station / sink will handle the data collection
                    n["object"].send(min_dis)
                else:
                    # Data will be transmitted to the nearest c
                    n["object"].send(min_dis)
                    node_collection[node_collection.index(n["tx_rx_node"])]["object"].receive()
    else:
        logger.info("No transmission for this round.")  # Bug? Should send to BS instead

    stats.append(len(node_collection))


# Test
import matplotlib.pyplot as plt
plt.figure(1)
plt.plot([x for x in range(len(stats))], stats, "k-")
plt.axvline(x=stats.count(nodes_number), c='r', ls=":")
plt.text(x=stats.count(nodes_number), y=0, s=" x = {}".format(stats.count(nodes_number)))
plt.savefig(fname="leach-{}.svg".format(timestamp))
