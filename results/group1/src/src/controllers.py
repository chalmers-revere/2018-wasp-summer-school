
class angle_controller:
    def __init__(self, r, Kp=1):
        self.u = 0
        self.r = r
        self.Kp = Kp
        
    def calc_u(self, y):
        e = self.r - y
        self.u = self.Kp*e

        return self.u

class speed_controller:
    
    def __init__(self, r, Kp=1, Kd=0, N=10, h=0.05):
        self.u = 0
        self.r = r
        self.Kp = Kp
        self.Kd = Kd
        self.N = N
        self.h = h
        self.y_old = 0
        
        self.P = 0
        self.D = 0

    def change_h(self, h):
        self.h = h

    def calc_u(self, y):
        
        e = self.r - y
        
        ad = self.Kd / (self.Kd + self.N*self.h)
        bd = self.Kp*ad*self.N

        self.P = self.Kp*(self.r - y)
        self.D =  ad*self.D - bd*(y - self.y_old)

        self.y_old = y
        self.u = self.P + self.D

        return self.u
            





