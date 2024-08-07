import argparse
from cgi import test
import os
import torch
import time
import sys
from models.mpc_fusion import MPC as net
from utils import utils_image as util
from data.dataloder import Dataset as D
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from fvcore.nn import FlopCountAnalysis, parameter_count_table
from PIL import Image

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=str, default='fusion', help='classical_sr, lightweight_sr, real_sr, '
                                                                     'gray_dn, color_dn, jpeg_car')
    parser.add_argument('--scale', type=int, default=1, help='scale factor: 1, 2, 3, 4, 8')  # 1 for dn and jpeg car
    parser.add_argument('--large_model', action='store_true', help='use large model, only provided for real image sr')
    parser.add_argument('--model_path', type=str,
                        default='./Model/Infrared_Visible_Fusion/Infrared_Visible_Fusion/models/')
    parser.add_argument('--iter_number', type=str,
                        default='100000')
    parser.add_argument('--root_path', type=str, default='./Dataset/testsets/',
                        help='input test image root folder')
    parser.add_argument('--dataset', type=str, default='MSRS',
                        help='input test image name')
    parser.add_argument('--A_dir', type=str, default='IR',
                        help='input test image name')
    parser.add_argument('--B_dir', type=str, default='VI_RGB', ##这 VI_RGB VI
                        help='input test image name')
    parser.add_argument('--tile', type=int, default=None, help='Tile size, None for no tile during testing (testing as a whole)')
    parser.add_argument('--tile_overlap', type=int, default=1, help='Overlapping of different tiles')
    parser.add_argument('--in_channel', type=int, default=1, help='3 means color image and 1 means gray image')
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    # set up model
    model_path = os.path.join(args.model_path, args.iter_number + '_G.pth')
    if os.path.exists(model_path):
        print(f'loading model from {args.model_path}')
    else:
        print('Traget model path: {} not existing!!!'.format(model_path))
        sys.exit()
    model = define_model(args)
    print(parameter_count_table(model))
    model.eval()
    model = model.to(device)

    # setup folder and path
    folder, save_dir, border, window_size = setup(args)
    a_dir = os.path.join(args.root_path, args.dataset, args.A_dir)
    b_dir = os.path.join(args.root_path, args.dataset, args.B_dir)
    print(a_dir)
    os.makedirs(save_dir, exist_ok=True)
    test_set = D(a_dir, b_dir, args.in_channel)

    test_loader = DataLoader(test_set, batch_size=1,
                                     shuffle=False, num_workers=1,
                                     drop_last=False, pin_memory=True)
    start = time.time()
    for i, test_data in enumerate(test_loader):
        imgname = test_data['A_path'][0]
        imgname_VIS = test_data['B_path'][0]
        img_a = test_data['A'].to(device)
        img_b = test_data['B'].to(device)

        with torch.no_grad():
            # pad input image to be a multiple of window_size
            _, _, h_old, w_old = img_a.size()
            xx = 32
            if h_old % xx != 0  or w_old % xx != 0:
                h_new = int(torch.ceil(torch.Tensor([h_old]) / (xx))) * (xx)
                w_new = int(torch.ceil(torch.Tensor([w_old]) / (xx))) * (xx)

                padding_h = h_new - h_old
                padding_w = w_new - w_old

                img_a = torch.nn.functional.pad(img_a, (0, padding_w, 0, padding_h))
                img_b = torch.nn.functional.pad(img_b, (0, padding_w, 0, padding_h))

            net.convert_pos(model,img_a, model)
            output = test(img_a, img_b, model, args, window_size)
            if h_old % xx != 0 or w_old % xx != 0:
                top = 0
                bottom = output.shape[2] - padding_h
                left = 0
                right = output.shape[3] - padding_w
                output = output[: ,: , top:bottom,left:right]
            output = output.detach()[0].float().cpu()
        output = util.tensor2uint(output)
        save_name = os.path.join(save_dir, os.path.basename(imgname))
        if args.dataset == 'MSRS':
            xx = Image.open(imgname_VIS).convert('YCbCr')
            y, cb, cr = xx.split()
            output = transforms.ToPILImage()(output)
            img = Image.merge('YCbCr', [output, cb, cr]).convert('RGB')
            img.save(save_name)
        else:
            util.imsave(output, save_name)
    end = time.time()
    print("[{}/{}]  Saving fused image to : {}, Processing time is {:4f} s".format(i + 1, len(test_loader), save_name,end - start))
def define_model(args):
    # model = net(upscale=args.scale, in_chans=args.in_channel, img_size=128, window_size=8,
    #             img_range=1., depths=[6, 6, 6, 6], embed_dim=60, num_heads=[6, 6, 6, 6],
    #             mlp_ratio=2, upsampler=None, resi_connection='1conv')
    model = net(in_chans=args.in_channel, img_size=128, num_heads=[1,2]) #改
    param_key_g = 'params'
    model_path = os.path.join(args.model_path, args.iter_number + '_E.pth')
    pretrained_model = torch.load(model_path)
    model.load_state_dict(pretrained_model[param_key_g] if param_key_g in pretrained_model.keys() else pretrained_model, strict=True)
    
        
    return model


def setup(args):   
    save_dir = f'results/MPCFusion_{args.dataset}'
    folder = os.path.join(args.root_path, args.dataset, 'A_Y')
    print('folder:', folder)
    border = 0
    window_size = 8

    return folder, save_dir, border, window_size


def get_image_pair(args, path, a_dir=None, b_dir=None):
    a_path = os.path.join(a_dir, os.path.basename(path))
    b_path = os.path.join(b_dir, os.path.basename(path))
    print("A image path:", a_path)
    assert not args.in_channel == 3 or not args.in_channel == 1, "Error in input parameters "
    img_a = util.imread_uint(a_path, args.in_channel)
    img_b = util.imread_uint(b_path, args.in_channel)
    img_a = util.uint2single(img_a)
    img_b = util.uint2single(img_b)
    return os.path.basename(path), img_a, img_b


def test(img_a, img_b, model, args, window_size):
    if args.tile is None:
        # test the image as a whole
        #print(model.state_dict())
        output = model(img_a, img_b)
    else:
        # test the image tile by tile
        b, c, h, w = img_a.size()
        tile = min(args.tile, h, w)
        assert tile % window_size == 0, "tile size should be a multiple of window_size"
        tile_overlap = args.tile_overlap
        sf = args.scale

        stride = tile - tile_overlap
        h_idx_list = list(range(0, h-tile, stride)) + [h-tile]
        w_idx_list = list(range(0, w-tile, stride)) + [w-tile]
        E = torch.zeros(b, c, h*sf, w*sf).type_as(img_a)
        W = torch.zeros_like(E)

        for h_idx in h_idx_list:
            for w_idx in w_idx_list:
                in_patch = img_a[..., h_idx:h_idx+tile, w_idx:w_idx+tile]
                out_patch = model(in_patch)
                out_patch_mask = torch.ones_like(out_patch)

                E[..., h_idx*sf:(h_idx+tile)*sf, w_idx*sf:(w_idx+tile)*sf].add_(out_patch)
                W[..., h_idx*sf:(h_idx+tile)*sf, w_idx*sf:(w_idx+tile)*sf].add_(out_patch_mask)
        output = E.div_(W)

    return output

if __name__ == '__main__':
    main()
