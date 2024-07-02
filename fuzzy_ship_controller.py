import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import skfuzzy
import skfuzzy.control

from map import RayCastResult
from spaceship import Spaceship, ShipController

class FuzzyShipController(ShipController):
    def __init__(self, ship: Spaceship):
        super().__init__(ship)

        self.fig = None

        self.setup_inputs()
        self.setup_outputs()
        self.setup_control_system()
        self.simulation = skfuzzy.control.ControlSystemSimulation(self.control_system)

    def setup_inputs(self):
        
        # Terrain Collision 
        
        # Obviamente, controla a velocidade da nave. 
        # Universo: Varia de 0 a 200. 
        velocity = skfuzzy.control.Antecedent(np.arange(0, 200 + 1, 1), 'velocity')
        velocity['SLOW']    = skfuzzy.trapmf(velocity.universe, [0,    0,   0, 75])
        velocity['MEDIUM']  = skfuzzy.trapmf(velocity.universe, [50, 100, 100, 150])
        velocity['FAST']    = skfuzzy.trapmf(velocity.universe, [75, 200, 200, 200])

        # Controla o equilíbrio da nave, comparando distâncias entre raios lançados à esquerda e à direita.
        # Universo: Varia de -200 a 200.
        wall_balance = skfuzzy.control.Antecedent(np.arange(-200, 200 + 1, 1), 'w_balance')
        wall_balance['LEFT']     = skfuzzy.trapmf(wall_balance.universe, [-200, -200, -200, 0])
        wall_balance['CENTER']   = skfuzzy.trapmf(wall_balance.universe, [-50, 0, 0, 50])
        wall_balance['RIGHT']    = skfuzzy.trapmf(wall_balance.universe, [0, 200, 200, 200])

        # Controla a lateralidade da nave, comparando distâncias entre raios lançados à extrema esquerda e à extrema direita.
        # Universo: Varia de -100 a 100.
        wall_side = skfuzzy.control.Antecedent(np.arange(-100, 100 + 1, 1), 'w_side')
        wall_side['LEFT']    = skfuzzy.trapmf(wall_side.universe, [-100, -100, -100, 0])
        wall_side['CENTER']  = skfuzzy.trapmf(wall_side.universe, [-25, 0, 0, 25])
        wall_side['RIGHT']   = skfuzzy.trapmf(wall_side.universe, [0, 100, 100, 100])

        # Controla a proximidade da nave em relação ao objeto à sua frente.
        # Universo: Varia de -0 a 200.
        wall_head = skfuzzy.control.Antecedent(np.arange(0, 200 + 1, 1), 'w_head')
        wall_head['CLOSE']   = skfuzzy.trapmf(wall_head.universe, [ 0,  0,  25, 125])
        wall_head['AWAY']    = skfuzzy.trapmf(wall_head.universe, [75, 200, 200, 200])
        
        # Enemy Balance
        enemy_balance = skfuzzy.control.Antecedent(np.arange(-500, 500 + 1, 1), 'e_balance')
        enemy_balance['LEFT']     = skfuzzy.trapmf(enemy_balance.universe, [-500, -500, -500, 0])
        enemy_balance['CENTER']   = skfuzzy.trapmf(enemy_balance.universe, [-125, 0, 0, 125])
        enemy_balance['RIGHT']    = skfuzzy.trapmf(enemy_balance.universe, [0, 500, 500, 500])
        
        # Enemy Side
        enemy_side = skfuzzy.control.Antecedent(np.arange(-250, 250 + 1, 1), 'e_side')
        enemy_side['LEFT']    = skfuzzy.trapmf(enemy_side.universe, [-250, -250, -250, 0])
        enemy_side['CENTER']  = skfuzzy.trapmf(enemy_side.universe, [-25, 0, 0, 25])
        enemy_side['RIGHT']   = skfuzzy.trapmf(enemy_side.universe, [0, 250, 250, 250])

        # Enemy Head
        enemy_head = skfuzzy.control.Antecedent(np.arange(0, 500 + 1, 1), 'e_head')
        enemy_head['CLOSE']   = skfuzzy.trapmf(enemy_head.universe, [ 0,  0, 62.5, 312.5])
        enemy_head['AWAY']    = skfuzzy.trapmf(enemy_head.universe, [187.5, 500, 500, 500])

        self.inputs = [velocity, wall_balance, wall_side, wall_head, enemy_balance, enemy_side, enemy_head]

    def setup_outputs(self):
        # Aceleração
        gas = skfuzzy.control.Consequent(np.arange(0 - 0.25, 1 + 0.02 + 0.25, 0.02), 'gas')
        gas['NONE'] = skfuzzy.sigmf(gas.universe, 0.05, -40)
        gas['SOFT'] = skfuzzy.sigmf(gas.universe, 0.33, -10)
        gas['HARD'] = skfuzzy.sigmf(gas.universe, 0.75, 20)

        # Desaceleração
        brake = skfuzzy.control.Consequent(np.arange(0 - 0.25, 1 + 0.02 + 0.25, 0.02), 'brake')
        brake['NONE'] = skfuzzy.sigmf(brake.universe, 0.05, -40)
        brake['SOFT'] = skfuzzy.sigmf(brake.universe, 0.33, -10)
        brake['HARD'] = skfuzzy.sigmf(brake.universe, 0.75, 20)

        # Direção 
        steer = skfuzzy.control.Consequent(np.arange(-1 - 0.5, 1 + 0.05 + 0.5, 0.05), 'steer')
        steer['RIGHT'] = skfuzzy.sigmf(steer.universe, -0.5, -10)
        steer['NONE']  = skfuzzy.gaussmf(steer.universe, 0, 0.10)
        steer['LEFT']  = skfuzzy.sigmf(steer.universe, 0.5, 10)

        self.outputs = [gas, brake, steer]

    def setup_control_system(self):
        c = skfuzzy.control
        velocity, w_balance, w_side, w_head, e_balance, e_side, e_head = self.inputs
        gas, brake, steer = self.outputs

        self.control_system = c.ControlSystem([
            c.Rule(w_balance['LEFT'], steer['RIGHT']),
            c.Rule(w_balance['RIGHT'], steer['LEFT']),
            c.Rule(w_balance['CENTER'] & w_side['CENTER'], steer['NONE'] % 0.1),

            c.Rule(w_side['LEFT'], steer['RIGHT']),
            c.Rule(w_side['RIGHT'], steer['LEFT']),

            c.Rule(w_head['CLOSE'], (brake['HARD'], gas['SOFT'])),
            c.Rule(w_head['AWAY'] & w_balance['CENTER'], (brake['NONE'], gas['SOFT'])),
            c.Rule(w_head['AWAY'] & ~w_balance['CENTER'], (brake['NONE'], gas['SOFT'])),

            c.Rule(e_balance['LEFT'], steer['LEFT']),
            c.Rule(e_balance['RIGHT'], steer['RIGHT']),
            c.Rule(e_balance['CENTER'] & e_side['CENTER'], steer['NONE'] % 0.1),

            c.Rule(e_side['LEFT'], steer['LEFT']),
            c.Rule(e_side['RIGHT'], steer['RIGHT']),
            
            c.Rule(e_head['AWAY'], (gas['SOFT'])),

            c.Rule(velocity['SLOW'], gas['SOFT']),
        ])

    def update_simulation(self, wall_sensors: dict[str, RayCastResult], enemy_sensors: dict[str, RayCastResult]):
        
        # Wall Sensors
        self.simulation.input['velocity'] = self.ship.velocity
        self.simulation.input['w_balance'] = wall_sensors['left'].distance - wall_sensors['right'].distance
        self.simulation.input['w_side'] = wall_sensors['hard_left'].distance - wall_sensors['hard_right'].distance
        self.simulation.input['w_head'] = wall_sensors['head'].distance

        # Enemy Sensors
        self.simulation.input['e_balance'] = enemy_sensors['left'].distance - enemy_sensors['right'].distance
        self.simulation.input['e_side'] = enemy_sensors['hard_left'].distance - enemy_sensors['hard_right'].distance
        self.simulation.input['e_head'] = enemy_sensors['head'].distance
        
        self.simulation.compute()
        self.gas = max(0, self.simulation.output['gas']) # other are properly clamped in the base ship controller
        self.brake = self.simulation.output['brake']
        self.steer = self.simulation.output['steer']
        
        if (enemy_sensors['head'].distance < 500): 
            self.ship.fire_projectiles(1)

    def update(self, dt: float, *args, **kwargs):
        # self.update_simulation(sensors) # need to be called separately
        super().update(dt, *args, **kwargs)
