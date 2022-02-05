import asyncio
import os
import socketserver
from datetime import datetime
from concurrent.futures.thread import ThreadPoolExecutor

import aioconsole
import narupa.mdanalysis
import narupa.openmm.serializer
from MDAnalysis import Universe


class Util:
    stopServer = False


if not os.path.isdir(".\\logs"):
    os.mkdir(".\\logs")
log = open(datetime.now().strftime(".\\logs\\Server_exceptions_%d_%m_%y_%H_%M_%S") + ".log", "a")


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            data = self.rfile.readline().decode("utf-8")
            #print("\r" + self.data + "\n>>> ", end="")
            if data == 'q':
                Util.stopServer = True
                return
            if data == '':
                return
            narupaServer.draw(data)
        except Exception as e:
            print("\r" + str(e) + "\n>>> ")
            log.write("[" + datetime.now().strftime("%H:%M:%S") + "]" + str(e))
            log.flush()


class TCPServer:
    def __init__(self, host="localhost", port=7777):
        self._host = host
        self._port = port

    def start(self):
        with socketserver.TCPServer((self._host, self._port), Handler) as self.server:
            self.server.serve_forever()

    def close(self):
        self.server.shutdown()


class NarupaServer:
    def __init__(self):
        from narupa.app import NarupaFrameApplication
        self.frame_server = NarupaFrameApplication.basic_server()

    def draw(self, molecule_path):
        try:
            universe = Universe(molecule_path)
            frame = narupa.mdanalysis.mdanalysis_to_frame_data(universe)
            self.frame_server.frame_publisher.send_frame(0, frame)
            self.design()
            print("\rAccepted " + molecule_path + "\n>>> ", end="")
            # narupa.openmm.serializer.serialize_simulation(self.frame_server)
        except Exception as e:
            print("\r" + str(e) + "\n>>> ")
            log.write("[" + datetime.now().strftime("%H:%M:%S") + "]" + str(e))
            log.flush()

    def design(self):
        from narupa.app import NarupaImdClient
        client = NarupaImdClient.connect_to_single_server(port=self.frame_server.port)

        client.subscribe_multiplayer()

        with client.root_selection.modify() as selection:
            selection.interaction_method = 'single'
            cpk_colours = {
                'O': 'red',
                'N': 'blue',
                'H': 'white',
                'Cl': 'green',
                'S': 'yellow',
                'C': 'black',
                'F': 'grey',
                'K': '#08F0F3',
                'Cu': 'orange',
                'Br': '#BFF308',
                'Li': '#8B3E02',
                'Ca': '#B104C2',
                'Mg': '#568903',
                'Si': '#F8F895',
                'I': '#70BEBF',
                'P': 'pink'
            }
            selection.renderer = {
                'color': {
                    'type': 'cpk',
                    'scheme': cpk_colours,
                }
            }

    def close(self):
        self.frame_server.close()


async def get_input():
    print(">>> ", end="")
    while not Util.stopServer:
        input_line = await aioconsole.ainput()
        if input_line:
            if input_line == 'q':
                Util.stopServer = True
                break
            if not os.path.isfile(input_line):
                print(input_line + " не является файлом")
                continue
            narupaServer.draw(input_line)


socketServer = TCPServer()
narupaServer = NarupaServer()


def checkClose():
    while True:
        if Util.stopServer:
            socketServer.close()
            narupaServer.close()
            print("\rСервер завершил работу, нажмите Enter для продолжения", end="")
            break


def closeServers():
    narupaServer.close()
    socketServer.close()


with ThreadPoolExecutor() as executor:
    executor.submit(socketServer.start)
    executor.submit(checkClose)
    executor.submit(asyncio.run, get_input())

log.close()

# def run_window():
#     file_list_column = [
#         [
#             sg.Text("Files"),
#             sg.In(size=(25, 1), enable_events=True, key="-FILES-"),
#             sg.FilesBrowse(),
#         ],
#         [
#             sg.Listbox(values=[], enable_events=True, size=(80, 20), key="-FILE LIST-", auto_size_text=True)
#         ],
#     ]
#
#     file_runner_column = [
#         [sg.Text("Choose a file from the list")],
#         [sg.Text(size=(80, 1), key="-TOUT-")],
#         [sg.Button('Run', key="-RUN-")],
#         [sg.Text("Current running:")],
#         [sg.Text(size=(80, 1), key="-CURRENT_RUNNING-")],
#     ]
#
#     layout = [
#         [
#             sg.Column(file_list_column),
#             sg.VSeperator(),
#             sg.Column(file_runner_column),
#         ]
#     ]
#
#     window = sg.Window("Narupa Server", layout, resizable=True)
#
#     while True:
#         event, values = window.read()
#         if event == "Exit" or event == sg.WIN_CLOSED:
#             server.close()
#             window.close()
#             break
#         if event == "-FILES-":
#             files = values["-FILES-"]
#             window["-FILE LIST-"].update(files.split(';'))
#         if event == "-FILE LIST-":  # A file was chosen from the listbox
#             try:
#                 filename = values["-FILE LIST-"][0]
#                 window["-TOUT-"].update(filename)
#             except:
#                 pass
#         if event == "-RUN-":  # A file was chosen from the listbox
#             try:
#                 server.draw(values["-FILE LIST-"][0])
#                 window["-CURRENT_RUNNING-"].update(values["-FILE LIST-"][0])
#                 # print([values["-FILE LIST-"][0]])
#             except Exception as e:
#                 window["-CURRENT_RUNNING-"].update("Error: " + str(e))
#                 print(e)
#                 pass
