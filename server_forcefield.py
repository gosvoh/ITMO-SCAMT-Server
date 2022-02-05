import asyncio
import os
import socketserver
from datetime import datetime
from concurrent.futures.thread import ThreadPoolExecutor

import aioconsole
from narupa.openmm import OpenMMRunner
from narupa.openmm.imd import add_imd_force_to_system
from simtk.openmm import app, unit, openmm


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
            narupaServer.run(data)
        except Exception as e:
            print("\r" + str(e) + "\n>>> ")
            log.write("[" + datetime.now().strftime("%H:%M:%S") + "]" + str(e))
            log.flush()


class TCPServer:
    def __init__(self, HOST="localhost", PORT=7777):
        self.PORT = PORT
        self.HOST = HOST

    def start(self):
        with socketserver.TCPServer((self.HOST, self.PORT), Handler) as self.server:
            self.server.serve_forever()

    def close(self):
        self.server.shutdown()


# noinspection DuplicatedCode
class NarupaServer:
    def __init__(self):
        self.serverStarted = False
        self.level = ""
        self.closed = True
        self.forcefield = app.ForceField('ff99SB.xml', 'tip3p_standard.xml')

    def _design(self, server):
        from narupa.app import NarupaImdClient
        client = NarupaImdClient.connect_to_single_server(port=server.port)

        client.subscribe_multiplayer()

        with client.root_selection.modify() as selection:
            selection.interaction_method = 'group'
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

    def run(self, file):
        if not self.closed:
            return
        if self.level == file:
            return
        try:
            
            pdb = app.PDBFile(file)
            self.level = file
            system = self.forcefield.createSystem(
                pdb.topology,
                nonbondedMethod=app.PME,
                nonbondedCutoff=1 * unit.nanometer,
                constraints=app.HBonds,
                removeCMMotion=False,
            )

            add_imd_force_to_system(system)

            integrator = openmm.LangevinIntegrator(
                300 * unit.kelvin,
                1 / unit.picosecond,
                0.002 * unit.picoseconds,
            )
            simulation = app.Simulation(pdb.topology, system, integrator)
            simulation.context.setPositions(pdb.positions)

            self.runner = OpenMMRunner(simulation=simulation)
            self.runner.run()
            self._design(self.runner.app_server)
            self.closed = False
            print("\rAccepted " + file + "\n>>> ", end="")
        except Exception as e:
            print("\r" + str(e) + "\n>>> ")
            log.write("[" + datetime.now().strftime("%H:%M:%S") + "]" + str(e))
            log.flush()

    def close(self):
        self.runner.close()
        self.closed = True


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
            narupaServer.run(input_line)


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