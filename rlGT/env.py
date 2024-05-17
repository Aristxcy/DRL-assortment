import numpy as np
from uti import create_data
import torch
import time
class market_dynamic:
    def __init__(self,args,initial_inventory,products_price,Train=False):
        self.device = args.device
        self.batch_size = args.train_batch_size if Train else args.batch_size
        self.inventory_level = np.tile(initial_inventory, (self.batch_size, 1))
        self.initial_inventory = np.tile(initial_inventory, (self.batch_size, 1))
        self.total_inv = initial_inventory.sum()
        self.products_price=products_price
        self.num_of_products=len(initial_inventory)
        self.cardinality = args.cardinality
        self.purchase=np.zeros((self.batch_size,self.num_of_products),dtype= np.int)
        self.T=0#剩余的销售时间
        self.num_of_customer_segment = 4

        self.cus_type = args.cus_type
        self.rank_list = args.rank_list
        self.num_rl = len(self.rank_list)
        self.arrivals = 0
    def reset(self,initial_inventory,T):
        self.inventory_level = np.tile(initial_inventory, (self.batch_size, 1))
        self.T=T
        self.arrivals = 0
    def step(self,arriving_seg,assortment,check=False):#assortment是torch.zeros([env.batch_size, self.num_products],dtype=torch.int)
        #考虑batch,生成input
        pre = time.time()
        if check:
            breakpoint()
        if self.inventory_level.any() == 0:
            self.T-=1
            return None,np.array([[0]])
        arriving_cus = self.cus_type[arriving_seg].reshape(self.batch_size,self.num_rl)#每一行是这个cus type的list概率
        arriving_rl = torch.multinomial(torch.from_numpy(arriving_cus), 1)#sample出来的rank list的index
        b_rl= self.rank_list[arriving_rl].reshape(self.batch_size,self.num_of_products+1)#里面是每一个来的cus type这次的rank list
        ass = np.hstack((assortment,np.ones((self.batch_size,1))))
        ass = np.repeat(np.arange(1,self.num_of_products+2).reshape(1,self.num_of_products+1),self.batch_size,0)*ass
        ass = ass.reshape(self.batch_size,self.num_of_products+1,1)
        index = []#选的商品代号
        for b in range(self.batch_size):
            index.append(b_rl[b][np.min(np.where(b_rl[b]==ass[b])[-1])])#[-1]取的是ass中的元素在ranklist里面的index，np.min找出来的是ass里面元素在b_rl里面最靠前的那个位置，这个索引找出来的最靠前的prod
        index = torch.tensor(index, dtype=torch.int64).reshape(self.batch_size,-1)-1#0到10
        prices = np.hstack((self.products_price,np.array([0])))
        self.purchase = torch.zeros((self.batch_size, self.num_of_products+1))
        self.purchase.scatter_(1,index,1)
        index = index.numpy()
        reward = prices[index]
        self.inventory_level-=self.purchase[:,:-1].numpy()#最后一列代表不买
        self.T-=1
        self.arrivals += 1
        now = time.time()
        #print('time:', now-pre)
        #breakpoint()
        return index,reward
    def get_mask(self):
        mask = self.inventory_level.copy()
        mask[self.inventory_level == 0] = 1
        mask[self.inventory_level > 0]=0
        return mask
    def all_finished(self):
        if self.T == 1:
            return True
        else:
            return False
        
        
class market_dynamic_Net:
    def __init__(self,args,Resnet,initial_inventory,products_price,Train=False):
        self.args = args
        self.net = Resnet
        self.device = args.device
        self.batch_size = args.train_batch_size if Train else args.batch_size
        self.inventory_level = np.tile(initial_inventory, (self.batch_size, 1))
        self.initial_inventory = np.tile(initial_inventory, (self.batch_size, 1))
        self.total_inv = initial_inventory.sum()
        self.products_price=products_price
        self.num_of_products=len(initial_inventory)
        self.cardinality = args.cardinality
        self.purchase=np.zeros((self.batch_size,self.num_of_products))
        self.T=0#剩余的销售时间
        self.arrivals = 0
    def reset(self,initial_inventory,T):
        self.inventory_level = np.tile(initial_inventory, (self.batch_size, 1))
        self.T=T
        self.arrivals = 0
    def step(self,arriving_seg,assortment):#assortment是torch.zeros([env.batch_size, self.num_products],dtype=torch.int)
        # 关键语句
        with torch.no_grad():
            prob = torch.softmax(self.net[int(arriving_seg)](torch.from_numpy(np.hstack((assortment,np.array([[1]])))).float()),1) 
        # 初始化
        prices = np.hstack((self.products_price,np.array([0])))
        index = torch.multinomial(prob,1).cpu()
        self.purchase = torch.zeros((self.batch_size, self.num_of_products+1))
        self.purchase.scatter_(1,index,1)
        index = index.numpy()
        reward = prices[index]
        self.inventory_level-=self.purchase[:,:-1].numpy().astype(np.int64) #最后一列是不买
        self.T-=1
        self.arrivals += 1
        now = time.time()
        #print('time:', now-pre)
        #breakpoint()
        return index,reward
    def get_mask(self):
        mask = self.inventory_level.copy()
        mask[self.inventory_level == 0] = 1
        mask[self.inventory_level > 0]=0
        return mask
    def all_finished(self):
        if self.T == 1:
            return True
        else:
            return False        
        
        