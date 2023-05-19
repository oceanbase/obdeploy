// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/deployments/:name/recover': (req: Request, res: Response) => {
    res.status(200).send({
      code: 92,
      data: {
        total: 65,
        items: [
          { name: '文勇', old_value: null, new_value: null },
          { name: '夏霞', old_value: null, new_value: null },
          { name: '蒋敏', old_value: null, new_value: null },
          { name: '龙洋', old_value: null, new_value: null },
          { name: '张明', old_value: null, new_value: null },
          { name: '姚芳', old_value: null, new_value: null },
          { name: '张勇', old_value: null, new_value: null },
          { name: '贺勇', old_value: null, new_value: null },
          { name: '沈军', old_value: null, new_value: null },
          { name: '贺丽', old_value: null, new_value: null },
          { name: '冯平', old_value: null, new_value: null },
          { name: '程秀兰', old_value: null, new_value: null },
          { name: '贾杰', old_value: null, new_value: null },
        ],
      },
      msg: '水广证达世许决往想果计清米光难求况变。',
      success: true,
    });
  },
};
