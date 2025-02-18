# Packages needed to build graph
import os # used to save graph as well
import argparse
import networkx as nx
import hashlib

# Packages needed to display graph
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.image as mpimg
from pyvis.network import Network
from IPython.display import HTML
import webbrowser

# Packages needed to save graph
from datetime import date
from datetime import datetime



def parse_user_input():
    """ Read input variables and parse command-line arguments """

    parser = argparse.ArgumentParser(
        description='Search and build graph of related files.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('-d', '--directory', type=str, default=os.path.dirname(__file__), help='Path to root directory to search with os.walk()')
    parser.add_argument('-t', '--filetype', type=str, default='Singularity', choices=['Singularity', 'Docker'], help='File type to search')
    parser.add_argument('-p', '--prefix', type=str, default='Singularity.', help='File naming prefix to search')
    parser.add_argument('-v', '--visualization', type=str, default='networkx', choices=['networkx','pyvis'], help='Choose visualization method')
    parser.add_argument('-f', '--filetype_to_save', type=str, nargs='+', choices=['JPEG', 'GEXF', 'GRAPHML'], help='Filetype(s) to use when saving the graph')
    parser.add_argument('-sd', '--save_directory', type = str, default='/Users/ethanjin/Downloads/rehs_graphs/', help='Directory to save graph PNG file')
    parser.add_argument('-r', '--reload_graph', type=str, help='Graph to reload')
    parser.add_argument('-c', '--compare_graphs', action='store_true', help="Compare graphs")
    parser.add_argument('-g1', '--first_graph', type = str, help='Directory where first graph is')
    parser.add_argument('-g2', '--second_graph', type = str, help='Directory where second graph is')

    args = parser.parse_args()
    return args


def create_node(G, edge_list, child, parent, filepath):
    if child not in G.nodes():
        G.add_node(child,md5_hash=(hash_files("md5", filepath)),sha256_hash=(hash_files("sha256", filepath)),file_path=(filepath))
    else:
        if (G.nodes[child]["md5"] == ""):
            G.nodes[child]["md5"] = hash_files("md5", filepath)
            G.nodes[child]["sha256"] = hash_files("sha256", filepath)

    if (parent != ""):
        edge_list.append((child.strip(), parent.strip()))


def relabel_node(name):
    output_string = ""

    arr_string = name.split("-")

    for i in range(len(arr_string)):
        if (i==0):
            output_string = output_string + arr_string[i]
            continue
        else:
            if(arr_string[i].isalpha()):
                if (not arr_string[i-1].isalpha()):
                    output_string = output_string + '\\n'
            output_string = output_string + '-' + arr_string[i]

    return output_string


def parse_agent(agent, line):
    parent = ""

    if (agent == "localimage"):
        if (line.find("/") >= 0):
            parent = line[line.rfind("/")+1:]
        else:
            parent = line[len("From: "):]

    else:
        tag = line.split(":")
        parent = tag[-1]
    
    return parent


def build_graph(G, edge_list, args):
    for (root, dirs, files) in os.walk(args.directory):
        for filename in files:
            if (filename.find(args.prefix) >= 0):
                child = filename[len(args.prefix):]
                parent = ""

                child_filepath = os.path.join(root, filename)
                file = open(child_filepath, "r")
                
                agent = ""
                for line in file:
                    temp = line.strip()
                    if (temp.find("Bootstrap") == 0):
                        agent = temp[len("Bootstrap: "):].strip()

                    if (line[0:6] == "From: "):
                        parent = parse_agent(agent, line)
                        break

                if (agent != ""):
                    create_node(G, edge_list, child, parent, child_filepath)

    G.add_edges_from(edge_list)


def hash_files(type, path):
    hash_lib = None

    if (type == "md5"):
        hash_lib = hashlib.md5()
    if (type == "sha256"):
        hash_lib = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_lib.update(chunk)

    return hash_lib.hexdigest()


def display_graph(G, args, dir):
    if (args.visualization == "networkx"):
        G.graph['graph']={'rankdir':'BT','pack':'true','packmode':'graph'}
        G.graph['node']={'shape':'box'}
        G.graph['edges']={'arrowsize':'4.0'}
        A = nx.nx_agraph.to_agraph(G)
        A.layout('dot')

        image_format = 'png'
        if args.filetype_to_save != None:
            if 'JPEG' in args.filetype_to_save:
                image_format = 'jpg'

        # Set labels for each node to include MD5 and SHA256 attributes
        for node in A.nodes():
            md5_value = A.get_node(node).attr['md5_hash']
            sha256_value = A.get_node(node).attr['sha256_hash']
            node_name = relabel_node(str(node))

            # Split the md5_value and sha256_value into chunks of 8 characters each
            md5_chunks = [md5_value[i:i+16] for i in range(0, len(md5_value), 16)]
            sha256_chunks = [sha256_value[i:i+16] for i in range(0, len(sha256_value), 16)]

            # Create label text with chunks of 8 characters per line        
            md5_text = "\n".join(md5_chunks)
            sha256_text = "\n".join(sha256_chunks)
            label_text = f"{node_name}\n\nMD5:\n{md5_text}\n\nSHA256:\n{sha256_text}"

            A.get_node(node).attr['label'] = label_text

        A.draw(dir + '.' + image_format,format=image_format, prog='dot')
        img = mpimg.imread(dir + '.' + image_format)
        imgplot = plt.imshow(img)
        plt.show()
    
    if (args.visualization == "pyvis"):
        # Convert NetworkX graph to pyvis network
        pyvis_graph = Network(notebook=True, cdn_resources='in_line')  # Set notebook=False for HTML export

        # Add nodes and edges to pyvis graph
        for node in G.nodes():
            pyvis_graph.add_node(node)

        for edge in G.edges():
            pyvis_graph.add_edge(*edge)

        # Set some optional pyvis options (can be customized according to your preferences)
        pyvis_graph.show_buttons(filter_=['physics'])

        # Save the interactive graph as an HTML file
        html_file = 'build_graph.html'
        pyvis_graph.save_graph(html_file)  # Use save_graph method instead of show

        # Automatically open the HTML file using the default web browser
        webbrowser.open_new_tab("/Users/ethanjin/naked-singularity/definition-files/build_graph.html")


def directory_setup(args):
    today = str(date.today())
    now = datetime.now()
    current_time = str(now.strftime("%H_%M_%S"))

    if not (os.path.exists(args.save_directory)):
        print("This directory does not exist. One will be automatically created.")
        os.mkdir(args.save_directory)

    parent_dir = args.save_directory
    dir = today
    current_path = os.path.join(parent_dir, dir)

    if not os.path.exists(current_path):
        os.mkdir(current_path)

    return current_path + "/" + current_time


def save_graph(G, args, dir):
    if (args.filetype_to_save != None):
        if 'GEXF' in args.filetype_to_save:
            nx.write_gexf(G, dir + ".gexf")
        if 'GRAPHML' in args.filetype_to_save:
            nx.write_graphml_lxml(G, dir + ".graphml")


def reload_graph(args, dir):
    R = nx.read_graphml(args.reload_graph)
    display_graph(R, args, dir)


def compare_graphs(args):
    G1 = nx.read_graphml(args.first_graph)
    G2 = nx.read_graphml(args.second_graph)
        
    nodes_in_G1 = set(G1.nodes())
    nodes_in_G2 = set(G2.nodes())

    nodes_only_in_G1 = nodes_in_G1 - nodes_in_G2
    nodes_only_in_G2 = nodes_in_G2 - nodes_in_G1

    if (nodes_only_in_G1 == set()):
        nodes_only_in_G1 = "No nodes missing"
    if (nodes_only_in_G2 == set()):
        nodes_only_in_G2 = "No nodes missing"

    print("Nodes only in G1:", nodes_only_in_G1)
    print("Nodes only in G2:", nodes_only_in_G2)


def main():
    G = nx.DiGraph()
    edge_list = []

    args = parse_user_input()
    dir = directory_setup(args)

    if (args.reload_graph != None):
        reload_graph(args, dir)
    elif (args.compare_graphs):
        compare_graphs(args)
    else:
        build_graph(G, edge_list, args)
        display_graph(G, args, dir)
        save_graph(G, args, dir)


if __name__ == "__main__":
    main()