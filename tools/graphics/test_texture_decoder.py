import unittest
from catalog_np3f_textures import decode_tmem, pixel

class TextureDecoderTests(unittest.TestCase):
    def meta(self, fmt, siz, width=4, height=2, tmem=0):
        return {'width':width,'height':height,'tlut':'None',
                'tile':{'fmt':fmt,'siz':siz,'line':1,'tmem':tmem}}

    def test_known_channel_values(self):
        self.assertEqual(pixel(0,2,[0xF8,0x01]),(255,0,0,255))
        self.assertEqual(pixel(0,2,[0x07,0xC0]),(0,255,0,0))
        self.assertEqual(pixel(0,2,[0,0x3F]),(0,0,255,255))
        self.assertEqual(pixel(3,0,[9]),(146,146,146,255))
        self.assertEqual(pixel(3,1,[0xA3]),(170,170,170,51))
        self.assertEqual(pixel(3,2,[101,203]),(101,101,101,203))
        self.assertEqual(pixel(4,0,[6]),(102,102,102,102))
        self.assertEqual(pixel(4,1,[123]),(123,123,123,123))

    def test_odd_row_word_swap_and_nonzero_tmem(self):
        data=bytearray(4096);data[2048:2056]=bytes.fromhex('f80107c1003fffff')
        data[2056:2064]=bytes.fromhex('003ffffef80107c1')
        im=decode_tmem(self.meta(0,2,tmem=256),data)
        self.assertEqual([im.getpixel((x,0)) for x in range(4)],[(255,0,0,255),(0,255,0,255),(0,0,255,255),(255,255,255,255)])
        self.assertEqual(im.getpixel((0,1)),(255,0,0,255))
        self.assertEqual(im.getpixel((3,1)),(255,255,255,0))

    def test_rgba32_split_banks(self):
        data=bytearray(4096);data[0:4]=bytes([10,20,50,60]);data[2048:2052]=bytes([30,40,70,80])
        im=decode_tmem(self.meta(0,3,2,1),data)
        self.assertEqual([im.getpixel((x,0)) for x in range(2)],[(10,20,30,40),(50,60,70,80)])

    def test_nibble_order_and_wrap(self):
        data=bytearray(4096);data[4088]=0x1F;data[4]=0xA5
        im=decode_tmem(self.meta(4,0,2,2,tmem=511),data)
        self.assertEqual([im.getpixel((x,y)) for y in range(2) for x in range(2)],[(17,)*4,(255,)*4,(170,)*4,(85,)*4])

    def test_palette_rejected(self):
        m=self.meta(0,2);m['tlut']='RGBA16'
        with self.assertRaises(ValueError):decode_tmem(m,bytes(4096))

if __name__=='__main__':unittest.main()
